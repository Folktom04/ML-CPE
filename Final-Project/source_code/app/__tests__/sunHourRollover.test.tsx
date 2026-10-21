/**
 * Field test 21 Oct 2026: "ออกแดด" at 14:24 (skin III) said "จะเตือนราว 15:02". At 15:00 the home
 * screen fetched /predict again, which starts at the 15:00 hour, so the 14:00 hour was gone: the
 * card said "ยังคำนวณปริมาณ UV ที่ได้รับไม่ได้" and the 15:02 burn notification was cancelled.
 * The hours seen since the session started are now kept (`mergeHours`, `settings.sunHours`).
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { screen } from '@testing-library/react-native';

import { SunSessionCard } from '@/components/SunSessionCard';
import { BURN_FRACTION, mergeHours, sunStatus, WM2_PER_UVI } from '@/lib/dose';
import { DEFAULT_SETTINGS, parseSettings, type Settings } from '@/lib/settings';
import { MED_J_M2 } from '@/lib/skinQuiz';
import { syncLocalNotifications } from '@/lib/useLocalNotifications';

import { mkHours } from './fixtures';
import { MemoryStorage, renderWithSettings } from './helpers';

const N = jest.requireMock('expo-notifications');
const at = (iso: string) => Date.parse(iso);
const NIGHT = Array(13).fill(0); // 17:00-05:00, not daylight

// q90 (alert_uvi) as the API gave it on 21 Oct: 14:00 5.09, 15:00 2.54, 16:00 0.75
const ANSWER_1400 = mkHours('2026-10-21T14:00:00+07:00', [5.09, 2.54, 0.75, ...NIGHT]);
const ANSWER_1500 = mkHours('2026-10-21T15:00:00+07:00', [2.54, 0.75, ...NIGHT, 0.6]);
const START = at('2026-10-21T14:24:00+07:00');
const AFTER_ROLLOVER = at('2026-10-21T15:00:30+07:00');

// 80 % of MED III: 280 J/m2. 14:24-15:00 at 5.09 gives 5.09 x 0.025 x 2160 s = 274.86 J/m2,
// the rest (5.14 J/m2) at 2.54 takes 80.9 s, so the warning is at about 15:01:21.
const TARGET = BURN_FRACTION * MED_J_M2.III;
const DOSE_TO_1500 = 5.09 * WM2_PER_UVI * 2160;
const WARN_AT =
  at('2026-10-21T15:00:00+07:00') + ((TARGET - DOSE_TO_1500) / (2.54 * WM2_PER_UVI)) * 1000;

type Pending = { content: { data: { kind: string; at?: number } }; trigger: { date: number } };
async function pending(kind: string): Promise<Pending[]> {
  const all: Pending[] = await N.getAllScheduledNotificationsAsync();
  return all.filter((n) => n.content.data?.kind === kind);
}

const s = (patch: Partial<Settings> = {}): Settings => ({
  ...DEFAULT_SETTINGS,
  skinType: 'III',
  notifyEnabled: false,
  dailySummary: false,
  reapplyReminder: false,
  sunStartedAt: START,
  ...patch,
});

beforeEach(async () => {
  N.__reset();
  jest.clearAllMocks();
  N.getPermissionsAsync.mockResolvedValue({ granted: true, canAskAgain: true });
  await AsyncStorage.clear();
});

describe('mergeHours', () => {
  it('keeps the start hour from the old answer and takes the new answer for later hours', () => {
    const fresh = mkHours('2026-10-21T15:00:00+07:00', [9, 0.75]);
    const merged = mergeHours(ANSWER_1400.slice(0, 3), fresh, START);
    expect(merged.map((h) => h.time)).toEqual([
      '2026-10-21T14:00:00+07:00',
      '2026-10-21T15:00:00+07:00',
      '2026-10-21T16:00:00+07:00',
    ]);
    expect(merged[1].alert_uvi).toBe(9); // the newer answer wins
  });

  it('drops hours that end before the session started and is sorted', () => {
    const early = mkHours('2026-10-21T12:00:00+07:00', [7, 6]); // 12:00 and 13:00
    const merged = mergeHours([...ANSWER_1400.slice(0, 2), ...early], [], START);
    expect(merged.map((h) => h.time)).toEqual([
      '2026-10-21T14:00:00+07:00',
      '2026-10-21T15:00:00+07:00',
    ]);
  });
});

describe('after the hour changes', () => {
  it('the new answer alone cannot give the dose (the bug seen on the phone)', () => {
    const st = sunStatus(ANSWER_1500, 'III', START, AFTER_ROLLOVER);
    expect(st.fractionNow).toBeNull();
    expect(st.warnAt).toBeNull();
  });

  it('with the kept hours the dose and the warning time stay as before', () => {
    const before = sunStatus(ANSWER_1400, 'III', START, at('2026-10-21T14:25:00+07:00'));
    expect(before.warnAt).toBeCloseTo(WARN_AT, -1);
    const merged = mergeHours(ANSWER_1400, ANSWER_1500, START);
    const after = sunStatus(merged, 'III', START, AFTER_ROLLOVER);
    expect(after.warnAt).toBeCloseTo(WARN_AT, -1);
    expect(after.fractionNow).toBeCloseTo(
      (DOSE_TO_1500 + 2.54 * WM2_PER_UVI * 30) / MED_J_M2.III,
      6,
    );
  });

  it('the burn notification set at 14:25 is still there after the 15:00 refresh', async () => {
    await syncLocalNotifications(ANSWER_1400, s(), at('2026-10-21T14:25:00+07:00'));
    expect(await pending('burn')).toHaveLength(1);
    const merged = mergeHours(ANSWER_1400, ANSWER_1500, START);
    await syncLocalNotifications(ANSWER_1500, s(), AFTER_ROLLOVER, false, merged);
    const burn = await pending('burn');
    expect(burn).toHaveLength(1);
    expect(burn[0].content.data.at).toBeCloseTo(WARN_AT, -1);
  });

  it('the card shows the warning time, not "cannot compute"', async () => {
    const merged = mergeHours(ANSWER_1400, ANSWER_1500, START);
    await renderWithSettings(
      <SunSessionCard
        hours={ANSWER_1500}
        sessionHours={merged}
        skin="III"
        isDaylight
        nowMs={AFTER_ROLLOVER}
      />,
      new MemoryStorage({ skinType: 'III', sunStartedAt: START }),
    );
    expect(await screen.findByTestId('sun-warn-at')).toHaveTextContent(/จะเตือนราว 15:01/);
    expect(screen.queryByText(/ยังคำนวณปริมาณ UV ที่ได้รับไม่ได้/)).toBeNull();
  });

  it('when hours are really missing, the card says the data is incomplete (not "ไม่ถึง 80 %")', async () => {
    await renderWithSettings(
      <SunSessionCard hours={ANSWER_1500} skin="III" isDaylight nowMs={AFTER_ROLLOVER} />,
      new MemoryStorage({ skinType: 'III', sunStartedAt: START }),
    );
    expect(await screen.findByTestId('sun-warn-at')).toHaveTextContent(/ข้อมูลไม่ครบ/);
    expect(screen.queryByText(/ไม่ถึง 80 %/)).toBeNull();
  });
});

describe('settings.sunHours', () => {
  it('stored hours are read back; damaged ones fall back to []', () => {
    const ok = parseSettings(JSON.stringify({ sunHours: ANSWER_1400.slice(0, 2) }));
    expect(ok.sunHours).toEqual(ANSWER_1400.slice(0, 2));
    expect(parseSettings(JSON.stringify({ sunHours: [{ time: 'x' }] })).sunHours).toEqual([]);
    expect(parseSettings(JSON.stringify({ sunHours: 'no' })).sunHours).toEqual([]);
    expect(parseSettings(JSON.stringify({ sunHours: Array(49).fill(ANSWER_1400[0]) })).sunHours).toEqual([]);
    expect(DEFAULT_SETTINGS.sunHours).toEqual([]);
  });
});
