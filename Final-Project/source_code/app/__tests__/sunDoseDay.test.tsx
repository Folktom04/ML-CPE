/**
 * Field test 4 Oct 2026, 15:37: with low UV (q90 3.0) "ออกแดด" said "จะเตือนราว 08:06", i.e. 08:06
 * of the NEXT day, because the dose kept adding up over the night into tomorrow's hours. A
 * session counts only the sunny part of the day it started; if 80 % of the MED is not reached
 * before the sun is gone, there is no warning time and no burn notification.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { screen } from '@testing-library/react-native';

import { SunSessionCard } from '@/components/SunSessionCard';
import { burnNotification } from '@/lib/alertPlan';
import { BURN_FRACTION, sunStatus, WM2_PER_UVI } from '@/lib/dose';
import { replaceScheduled } from '@/lib/notifications';
import { DEFAULT_SETTINGS, type Settings } from '@/lib/settings';
import { MED_J_M2 } from '@/lib/skinQuiz';
import { syncLocalNotifications } from '@/lib/useLocalNotifications';

import { mkHours } from './fixtures';
import { MemoryStorage, renderWithSettings } from './helpers';

const N = jest.requireMock('expo-notifications');
const at = (iso: string) => Date.parse(iso);
const NIGHT = Array(12).fill(0); // 18:00-05:00, not daylight

// 4 Oct afternoon as on the phone: q90 3.0 at 15:00, then lower until sunset; 5 Oct morning rises
const AFTERNOON = mkHours('2026-10-04T15:00:00+07:00', [
  3.0, 1.5, 0.3, ...NIGHT, 0.6, 2, 4, 6, 8, 9,
]);
const LOW_START = at('2026-10-04T15:37:00+07:00');

// 4 Oct 06:00-17:00 at 8.1, night, then 5 Oct 06:00-11:00 at 8.1
const DAY = Array(12).fill(8.1);
const FLAT_2DAYS = mkHours('2026-10-04T06:00:00+07:00', [...DAY, ...NIGHT, ...Array(6).fill(8.1)]);
const HIGH_START = at('2026-10-04T10:08:00+07:00');

const NO_WARN_TEXT = 'วันนี้ UV ไม่พอจะถึง 80 % ของ MED ก่อนแดดหมด จึงไม่ตั้งเตือน';

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
  ...patch,
});

beforeEach(async () => {
  N.__reset();
  jest.clearAllMocks();
  N.getPermissionsAsync.mockResolvedValue({ granted: true, canAskAgain: true });
  await AsyncStorage.clear();
});

describe('(ก) low UV late in the day: no warning tomorrow', () => {
  it('sunStatus: no warning time, and it says the sun ends first', () => {
    const st = sunStatus(AFTERNOON, 'III', LOW_START, LOW_START);
    expect(st.warnAt).toBeNull();
    expect(st.notBeforeSunset).toBe(true);
  });

  it('the card says so (no "08:06")', async () => {
    await renderWithSettings(
      <SunSessionCard hours={AFTERNOON} skin="III" isDaylight nowMs={LOW_START} />,
      new MemoryStorage({ skinType: 'III', sunStartedAt: LOW_START }),
    );
    expect(await screen.findByTestId('sun-warn-at')).toHaveTextContent(NO_WARN_TEXT);
    expect(screen.queryByText(/08:06/)).toBeNull();
  });

  it('no burn notification is scheduled', async () => {
    await syncLocalNotifications(AFTERNOON, s({ sunStartedAt: LOW_START }), LOW_START);
    expect(await pending('burn')).toHaveLength(0);
  });

  it('a burn notification already scheduled for the next day is cancelled on sync', async () => {
    const tomorrow = at('2026-10-05T08:06:00+07:00');
    await replaceScheduled(['burn'], [burnNotification(tomorrow)], LOW_START);
    expect(await pending('burn')).toHaveLength(1);
    await syncLocalNotifications(AFTERNOON, s({ sunStartedAt: LOW_START }), LOW_START + 60e3);
    expect(await pending('burn')).toHaveLength(0);
  });
});

describe('(ข) high UV that reaches 80 % within the day: unchanged', () => {
  it('10:08 at q90 8.1 -> 10:31, exactly the old formula', () => {
    const st = sunStatus(FLAT_2DAYS, 'III', HIGH_START, HIGH_START);
    const expected = HIGH_START + ((BURN_FRACTION * MED_J_M2.III) / (8.1 * WM2_PER_UVI)) * 1000;
    expect(st.warnAt).toBe(expected);
    expect(new Date(st.warnAt! + 7 * 3600e3).toISOString().slice(11, 16)).toBe('10:31');
    expect(st.notBeforeSunset).toBe(false);
  });

  it('card and notification as before', async () => {
    await renderWithSettings(
      <SunSessionCard hours={FLAT_2DAYS} skin="III" isDaylight nowMs={HIGH_START} />,
      new MemoryStorage({ skinType: 'III', sunStartedAt: HIGH_START }),
    );
    expect(await screen.findByTestId('sun-warn-at')).toHaveTextContent(
      'จะเตือนราว 10:31 (ที่ประมาณ 80 % ของ MED)',
    );
    await syncLocalNotifications(FLAT_2DAYS, s({ sunStartedAt: HIGH_START }), HIGH_START);
    const [b] = await pending('burn');
    expect(b.trigger.date).toBe(sunStatus(FLAT_2DAYS, 'III', HIGH_START, HIGH_START).warnAt);
  });
});

describe('(ค) the % of the MED stops growing when the sun is gone', () => {
  it('same value at sunset, at night and the next morning', () => {
    const sunset = at('2026-10-04T18:00:00+07:00');
    const f = (iso: string) => sunStatus(FLAT_2DAYS, 'III', HIGH_START, at(iso)).fractionNow;
    const atSunset = f('2026-10-04T18:00:00+07:00');
    // 10:08 -> 18:00 at 8.1: 28,320 s x 0.2025 W/m2 / 350 J/m2
    expect(atSunset).toBeCloseTo(((sunset - HIGH_START) / 1000) * 8.1 * WM2_PER_UVI / 350, 6);
    expect(f('2026-10-04T21:00:00+07:00')).toBe(atSunset);
    expect(f('2026-10-05T09:00:00+07:00')).toBe(atSunset);
  });
});
