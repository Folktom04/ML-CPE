import { fireEvent, render, screen } from '@testing-library/react-native';

import { PlannerCard } from '@/components/PlannerCard';
import { WM2_PER_UVI } from '@/lib/dose';
import { planActivity, riskOf } from '@/lib/planner';
import { MED_J_M2 } from '@/lib/skinQuiz';

import { mkHours } from './fixtures';

const at = (iso: string) => Date.parse(iso);
// 06:00-18:00 daylight with a noon peak, then night
const DAY = [1, 3, 6, 9, 11, 12, 11, 9, 6, 3, 1, 0.5, 0, 0];
const START = '2026-11-07T06:00:00+07:00';

describe('planActivity', () => {
  it('finds the lowest-dose start times, without overlap, and the one to avoid', () => {
    const hours = mkHours(START, DAY);
    const plan = planActivity(hours, 'III', 60, at('2026-11-07T05:40:00+07:00'));
    // 17:00-18:00 at alert_uvi 0.5 = 45 J/m2 is the lowest, then 06:00-07:00 at 1 = 90 J/m2
    expect(plan.best[0].startMs).toBe(at('2026-11-07T17:00:00+07:00'));
    expect(plan.best[0].fraction).toBeCloseTo((0.5 * WM2_PER_UVI * 3600) / MED_J_M2.III, 6);
    expect(plan.best[1].startMs).toBe(at(START));
    expect(plan.best[1].fraction).toBeCloseTo((1 * WM2_PER_UVI * 3600) / MED_J_M2.III, 6);
    // best slots never overlap
    const [a, b, c] = plan.best;
    for (const [x, y] of [
      [a, b],
      [a, c],
      [b, c],
    ]) {
      expect(x.endMs <= y.startMs || x.startMs >= y.endMs).toBe(true);
    }
    // noon peak (11:00-12:00 at alert_uvi 12) is the slot to avoid
    expect(plan.worst!.startMs).toBe(at('2026-11-07T11:00:00+07:00'));
    expect(riskOf(plan.worst!.fraction)).toBe('high');
    // 05:40 is before the first forecast hour, so there is no "now" slot
    expect(plan.now).toBeNull();
  });

  it('skips spans that reach into the night and starts on the 30-minute grid', () => {
    const hours = mkHours(START, DAY);
    const from = at('2026-11-07T16:10:00+07:00');
    // 2 h from 16:10 always reaches 18:00 (night): nothing fits, not even "now"
    const long = planActivity(hours, 'I', 120, from);
    expect(long.best).toHaveLength(0);
    expect(long.now).toBeNull();
    // 1 h: "now" is 16:10-17:10; 17:00-18:00 is the lowest, 16:30 overlaps it
    const hour = planActivity(hours, 'I', 60, from);
    expect(hour.now!.startMs).toBe(from);
    expect(hour.best.map((s) => s.startMs)).toEqual([at('2026-11-07T17:00:00+07:00')]);
    const short = planActivity(hours, 'I', 30, from);
    expect(short.best.map((s) => s.startMs % (30 * 60 * 1000))).toEqual([0, 0, 0]);
  });

  it('recommends extra slots only below the 80 % warning, but always keeps the best one', () => {
    const hours = mkHours(START, DAY);
    const from = at('2026-11-07T05:40:00+07:00');
    const plan = planActivity(hours, 'I', 120, from);
    expect(plan.best[0]).toBeDefined();
    expect(plan.best.slice(1).every((s) => riskOf(s.fraction) !== 'high')).toBe(true);
    // all day at UVI 12: every slot is high, only the single best one is listed
    const flat = planActivity(mkHours(START, Array(12).fill(12)), 'I', 60, from);
    expect(flat.best).toHaveLength(1);
    expect(riskOf(flat.best[0].fraction)).toBe('high');
  });

  it('is empty for an empty forecast', () => {
    expect(planActivity([], 'III', 60, at(START))).toEqual({ best: [], worst: null, now: null });
  });
});

it('riskOf bands: < 50 % low, < 80 % mid, otherwise high', () => {
  expect(riskOf(0.49)).toBe('low');
  expect(riskOf(0.5)).toBe('mid');
  expect(riskOf(0.79)).toBe('mid');
  expect(riskOf(0.8)).toBe('high');
});

describe('PlannerCard', () => {
  const hours = mkHours(START, DAY);
  const now = at('2026-11-07T08:20:00+07:00');

  it('shows the best slots, the slot to avoid and "now" for the default activity', async () => {
    await render(<PlannerCard hours={hours} skin="III" nowMs={now} />);
    expect(screen.getByTestId('plan-best-0')).toHaveTextContent(/17:00–17:30/);
    expect(screen.getByTestId('plan-worst')).toHaveTextContent(/11:00–11:30/);
    expect(screen.getByTestId('plan-now')).toHaveTextContent(/ตอนนี้–08:50/);
    expect(screen.queryByTestId('plan-activity-hint')).toBeNull();
  });

  it('changes the length with the activity and shows its hint', async () => {
    await render(<PlannerCard hours={hours} skin="III" nowMs={now} />);
    await fireEvent.press(screen.getByTestId('plan-activity-swim'));
    expect(screen.getByTestId('plan-minutes-60').props.accessibilityState.selected).toBe(true);
    expect(screen.getByTestId('plan-activity-hint')).toHaveTextContent(/สะท้อน/);
    await fireEvent.press(screen.getByTestId('plan-minutes-120'));
    expect(screen.getByTestId('plan-now')).toHaveTextContent(/ตอนนี้–10:20/);
  });

  it('says so when no daylight span is long enough', async () => {
    await render(<PlannerCard hours={hours} skin="III" nowMs={at('2026-11-07T17:40:00+07:00')} />);
    expect(screen.getByTestId('plan-empty')).toBeTruthy();
  });
});
