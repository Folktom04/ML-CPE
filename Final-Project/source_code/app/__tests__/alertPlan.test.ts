import {
  burnNotification,
  COOLDOWN_MS,
  FALLBACK_DAYS,
  nextSummaryTime,
  planDaily,
  planReapply,
  planUvAlerts,
  type PlannedNotification,
} from '@/lib/alertPlan';

import { mkHours } from './fixtures';

const at = (iso: string) => Date.parse(iso);
const clock = (p: PlannedNotification) =>
  new Date(p.at + 7 * 3600e3).toISOString().slice(11, 16);
const allSayEstimate = (plan: PlannedNotification[]) =>
  plan.every((p) => `${p.title} ${p.body}`.includes('ประมาณ'));

// 05:00-20:00 on 29 Sep: peak 10.2 at 13:00
const DAY = mkHours(
  '2026-09-29T05:00:00+07:00',
  [0, 0.6, 2, 4, 6, 7.5, 9, 10, 10.2, 9.5, 7, 5.9, 4, 2, 0.8, 0],
);
const OPTS = { threshold: 8, skin: 'III' as const };

describe('planUvAlerts', () => {
  it('alerts when the rounded upper value reaches 8 (7.5 -> 8) and is safe again below 6', () => {
    const plan = planUvAlerts(DAY, at('2026-09-29T05:30:00+07:00'), OPTS);
    expect(plan.map((p) => [p.kind, clock(p)])).toEqual([
      ['uv_high', '10:00'], // alert_uvi 7.5 rounds to 8
      ['uv_safe', '17:00'], // 5.9 rounds to 6 (not < 6); 4 is < 6
    ]);
    expect(plan[0].title).toBe('UV สูงมาก ช่วง 10:00–11:00');
    expect(plan[0].body).toMatch(/ค่าบน 7\.5/);
    expect(plan[0].body).toMatch(/ผิวประเภท III อาจไหม้ในประมาณ 31 นาที/); // 350/(7.5*1.5)
    expect(allSayEstimate(plan)).toBe(true);
  });

  it('uses the threshold chosen in settings (6 and 11)', () => {
    const six = planUvAlerts(DAY, at('2026-09-29T05:30:00+07:00'), { ...OPTS, threshold: 6 });
    expect(six.map((p) => [p.kind, clock(p)])).toEqual([
      ['uv_high', '09:00'],
      ['uv_safe', '18:00'], // safe below 4: 4 is not < 4, 2 is
    ]);
    const eleven = planUvAlerts(DAY, at('2026-09-29T05:30:00+07:00'), { ...OPTS, threshold: 11 });
    expect(eleven).toEqual([]); // 10.2 rounds to 10
  });

  it('the hour already on screen is not notified, but sets the state (no duplicate alert)', () => {
    const plan = planUvAlerts(DAY, at('2026-09-29T11:20:00+07:00'), OPTS);
    expect(plan.map((p) => [p.kind, clock(p)])).toEqual([['uv_safe', '17:00']]);
  });

  it('no alerts at night, and the state resets after sunset', () => {
    const night = mkHours(
      '2026-09-29T17:00:00+07:00',
      [9, 9, 9, 9, 9],
      [false, false, false, false, true],
    );
    const plan = planUvAlerts(night, at('2026-09-29T16:30:00+07:00'), OPTS);
    expect(plan.map((p) => [p.kind, clock(p)])).toEqual([['uv_high', '21:00']]);
  });

  it('at most one alert of each kind per 3 h, also across app openings (history)', () => {
    const zigzag = mkHours('2026-09-29T09:00:00+07:00', [9, 4, 9, 4, 9, 4, 9]);
    const plan = planUvAlerts(zigzag, at('2026-09-29T08:30:00+07:00'), OPTS);
    const highs = plan.filter((p) => p.kind === 'uv_high').map(clock);
    const safes = plan.filter((p) => p.kind === 'uv_safe').map(clock);
    expect(highs).toEqual(['09:00', '13:00']); // 11:00 is only 2 h after 09:00
    expect(safes).toEqual(['10:00', '14:00']);
    for (const kind of ['uv_high', 'uv_safe']) {
      const t = plan.filter((p) => p.kind === kind).map((p) => p.at);
      t.slice(1).forEach((x, i) => expect(x - t[i]).toBeGreaterThanOrEqual(COOLDOWN_MS));
    }
    const history = [{ kind: 'uv_high' as const, at: at('2026-09-29T08:00:00+07:00') }];
    const later = planUvAlerts(zigzag, at('2026-09-29T08:30:00+07:00'), OPTS, history);
    // 09:00 is 1 h after 08:00 (skipped), 11:00 is 3 h after, 13:00 only 2 h after 11:00
    expect(later.filter((p) => p.kind === 'uv_high').map(clock)).toEqual(['11:00', '15:00']);
  });
});

describe('planDaily', () => {
  // 29 Sep 20:00 -> 1 Oct 07:00 (36 h), daytime 06:00-18:00
  const hours = mkHours(
    '2026-09-29T20:00:00+07:00',
    Array.from({ length: 36 }, (_, i) => {
      const h = (20 + i) % 24;
      return h >= 6 && h < 18 ? 10 - Math.abs(12 - h) : 0;
    }),
  );

  it('next 07:00 in Bangkok', () => {
    expect(nextSummaryTime(at('2026-09-29T06:59:00+07:00'))).toBe(at('2026-09-29T07:00:00+07:00'));
    expect(nextSummaryTime(at('2026-09-29T07:00:00+07:00'))).toBe(at('2026-09-30T07:00:00+07:00'));
  });

  it('summary for a day the forecast covers, then "open the app" for the next days', () => {
    const plan = planDaily(hours, at('2026-09-29T20:00:00+07:00'), { threshold: 8 });
    expect(plan).toHaveLength(FALLBACK_DAYS);
    expect(plan[0]).toMatchObject({ kind: 'daily_summary', at: at('2026-09-30T07:00:00+07:00') });
    expect(plan[0].title).toBe('UV วันนี้สูงสุดประมาณ 9.5 (สูงมาก)');
    expect(plan[0].body).toBe('ราว 12:00 (ค่าบนประมาณ 10.0) · ช่วงที่ถึงเกณฑ์เตือน 10:00–15:00');
    expect(plan.slice(1).every((p) => p.kind === 'daily_fallback')).toBe(true);
    expect(plan[1].at).toBe(at('2026-10-01T07:00:00+07:00')); // only 06:00-07:00 known
    expect(plan[1].title).toBe('เปิดแอปเพื่อดู UV วันนี้');
    expect(allSayEstimate(plan)).toBe(true);
  });
});

describe('planReapply and burn', () => {
  it('reminds 2 h after applying, but not when that is at night', () => {
    const { plan, reason } = planReapply(DAY, at('2026-09-29T10:15:00+07:00'));
    expect(reason).toBeNull();
    expect(plan && clock(plan)).toBe('12:15');
    const late = planReapply(DAY, at('2026-09-29T18:30:00+07:00'));
    expect(late.plan).toBeNull();
    expect(late.reason).toMatch(/ไม่มีแดด/);
    expect(allSayEstimate([plan!, burnNotification(at('2026-09-29T11:00:00+07:00'))])).toBe(true);
  });

  it('burn warning says it assumes full sun', () => {
    expect(burnNotification(1).body).toMatch(/อยู่กลางแดดเต็มที่/);
  });
});
