/**
 * Field test 4 Oct 2026: a scheduled notification may still be pending after its time (Android
 * delivers inexact alarms late; "UV สูง" set for 10:00 arrived 10:06). A re-plan in that gap used
 * to cancel it and, its time being past, never schedule it again, so it never arrived. Overdue
 * notifications must now survive a re-plan unless their reason is gone.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

import { sunStatus } from '@/lib/dose';
import { MAX_OVERDUE_MS, replaceScheduled } from '@/lib/notifications';
import { DEFAULT_SETTINGS, type Settings } from '@/lib/settings';
import { syncLocalNotifications } from '@/lib/useLocalNotifications';

import { mkHours } from './fixtures';

const N = jest.requireMock('expo-notifications');
const at = (iso: string) => Date.parse(iso);
const MIN = 60 * 1000;
// alert_uvi 8.1 all day (06:00-18:00), as on the field-test morning
const FLAT = mkHours('2026-10-04T06:00:00+07:00', Array(12).fill(8.1));
// rises to 10.2 at 13:00 (same shape as notifications.test.tsx), so "UV สูง" is planned
const RISING = mkHours('2026-09-29T05:00:00+07:00', [
  0, 0.6, 2, 4, 6, 7.5, 9, 10, 10.2, 9.5, 7, 5.9, 4, 2, 0.8, 0, 0, 0, 0, 0, 0, 0, 0, 0,
]);
const START = at('2026-10-04T10:08:00+07:00');
const WARN_AT = sunStatus(FLAT, 'III', START, START).warnAt!;

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

describe('burn warning ("ออกแดด")', () => {
  it('sanity: 80 % of the MED of skin III at UVI 8.1 is reached at about 10:31', () => {
    expect(new Date(WARN_AT + 7 * 3600e3).toISOString().slice(11, 16)).toBe('10:31');
  });

  it('keeps its planned time in data.at', async () => {
    await syncLocalNotifications(FLAT, s({ sunStartedAt: START }), START);
    const [b] = await pending('burn');
    expect(b.content.data.at).toBe(WARN_AT);
  });

  it('a re-plan after the warning time keeps the pending (late) warning', async () => {
    const settings = s({ sunStartedAt: START });
    await syncLocalNotifications(FLAT, settings, START);
    // e.g. pull-to-refresh at 10:33 while Android has not delivered the 10:31 alarm yet
    await syncLocalNotifications(FLAT, settings, WARN_AT + 2 * MIN);
    expect(await pending('burn')).toHaveLength(1);
    expect(N.cancelScheduledNotificationAsync).not.toHaveBeenCalled();
  });

  it('"เข้าร่มแล้ว" still cancels an overdue warning', async () => {
    await syncLocalNotifications(FLAT, s({ sunStartedAt: START }), START);
    await syncLocalNotifications(FLAT, s({ sunStartedAt: null }), WARN_AT + 2 * MIN);
    expect(await pending('burn')).toHaveLength(0);
  });

  it('a new session drops the overdue warning of the old one', async () => {
    await syncLocalNotifications(FLAT, s({ sunStartedAt: START }), START);
    const restart = WARN_AT + 2 * MIN;
    await syncLocalNotifications(FLAT, s({ sunStartedAt: restart }), restart);
    const left = await pending('burn');
    expect(left).toHaveLength(1);
    expect(left[0].trigger.date).toBe(sunStatus(FLAT, 'III', restart, restart).warnAt);
  });
});

describe('reapply reminder', () => {
  const REAPPLY = at('2026-10-04T11:52:00+07:00');

  it('an overdue reminder survives a re-plan; pressing again replaces it', async () => {
    const settings = s({ reapplyReminder: true, reapplyAt: REAPPLY });
    await syncLocalNotifications(FLAT, settings, REAPPLY - 2 * 3600e3);
    await syncLocalNotifications(FLAT, settings, REAPPLY + 2 * MIN);
    expect(await pending('reapply')).toHaveLength(1);

    const again = REAPPLY + 3 * MIN + 2 * 3600e3; // "ทาครีมอีกครั้งแล้ว" at 11:55
    await syncLocalNotifications(FLAT, s({ reapplyReminder: true, reapplyAt: again }), REAPPLY + 3 * MIN);
    const left = await pending('reapply');
    expect(left).toHaveLength(1);
    expect(left[0].trigger.date).toBe(again);
  });
});

describe('UV alerts', () => {
  it('an overdue "UV สูง" is kept while alerts are on, and cancelled when switched off', async () => {
    const now = at('2026-09-29T05:30:00+07:00');
    await syncLocalNotifications(RISING, s({ notifyEnabled: true }), now);
    const [high] = await pending('uv_high');
    expect(high).toBeDefined();
    const late = high.trigger.date + 3 * MIN;
    await syncLocalNotifications(RISING, s({ notifyEnabled: true }), late);
    expect((await pending('uv_high')).map((n) => n.trigger.date)).toContain(high.trigger.date);

    await syncLocalNotifications(RISING, s({ notifyEnabled: false }), late + MIN);
    expect(await pending('uv_high')).toHaveLength(0);
  });

  it('replaceScheduled without a keep rule still cancels overdue ones (old behaviour)', async () => {
    const t = at('2026-09-29T10:00:00+07:00');
    await replaceScheduled(['uv_high'], [{ kind: 'uv_high', at: t, title: 'x', body: 'ประมาณ' }], t - MIN);
    await replaceScheduled(['uv_high'], [], t + MIN, () => true);
    expect(await pending('uv_high')).toHaveLength(1);
    await replaceScheduled(['uv_high'], [], t + 2 * MIN);
    expect(await pending('uv_high')).toHaveLength(0);
  });
});

describe('older and long-overdue notifications', () => {
  it('a notification scheduled by the old code (no data.at) is cancelled on the first sync', async () => {
    // as scheduled before this change: data has only the kind, its time has passed
    await N.scheduleNotificationAsync({
      content: { title: 'old', body: 'ประมาณ', data: { kind: 'burn' } },
      trigger: { type: 'date', date: WARN_AT },
    });
    await syncLocalNotifications(FLAT, s({ sunStartedAt: START }), WARN_AT + 2 * MIN);
    const left = await pending('burn');
    expect(left.every((n) => typeof n.content.data.at === 'number')).toBe(true);
    expect(left).toHaveLength(0); // 80 % already passed: nothing new to schedule
  });

  it('same session, a newer forecast moves the warning into the future: one warning left', async () => {
    await syncLocalNotifications(FLAT, s({ sunStartedAt: START }), START);
    // lower UV than first forecast (alert_uvi 4): 80 % is not reached yet at 10:33
    const LOWER = mkHours('2026-10-04T06:00:00+07:00', Array(12).fill(4));
    const now = WARN_AT + 2 * MIN;
    const newWarn = sunStatus(LOWER, 'III', START, now).warnAt!;
    expect(newWarn).toBeGreaterThan(now);
    await syncLocalNotifications(LOWER, s({ sunStartedAt: START }), now);
    const left = await pending('burn');
    expect(left).toHaveLength(1);
    expect(left[0].content.data.at).toBe(newWarn);
  });

  it('an overdue, still-pending "UV สูง" does not lead to a second one within the 3 h cooldown', async () => {
    // 09:00 reaches 8, 10:00 is safe again (< 6), 11:00 reaches 8 again (2 h after 09:00)
    const BUMPY = mkHours('2026-10-04T08:00:00+07:00', [6, 8.5, 5, 9, 4, 2, 0.6, 0, 0, 0, 0, 0]);
    const settings = s({ notifyEnabled: true, alertThreshold: 8 });
    await syncLocalNotifications(BUMPY, settings, at('2026-10-04T08:30:00+07:00'));
    const first = await pending('uv_high');
    expect(first.map((n) => n.trigger.date)).toEqual([at('2026-10-04T09:00:00+07:00')]);

    await syncLocalNotifications(BUMPY, settings, at('2026-10-04T09:05:00+07:00'));
    expect((await pending('uv_high')).map((n) => n.trigger.date)).toEqual([
      at('2026-10-04T09:00:00+07:00'),
    ]);
  });

  it('MAX_OVERDUE_MS is 30 min: overdue by 10 min is kept, by 31 min it is cancelled', async () => {
    expect(MAX_OVERDUE_MS).toBe(30 * MIN);
    const t = at('2026-10-04T10:00:00+07:00');
    await replaceScheduled(['uv_high'], [{ kind: 'uv_high', at: t, title: 'x', body: 'ประมาณ' }], t - MIN);
    await replaceScheduled(['uv_high'], [], t + 10 * MIN, () => true);
    expect(await pending('uv_high')).toHaveLength(1);
    await replaceScheduled(['uv_high'], [], t + 31 * MIN, () => true);
    expect(await pending('uv_high')).toHaveLength(0);
  });

  it('the age limit applies to every kind, e.g. a burn warning 31 min late', async () => {
    const settings = s({ sunStartedAt: START });
    await syncLocalNotifications(FLAT, settings, START);
    await syncLocalNotifications(FLAT, settings, WARN_AT + 10 * MIN);
    expect(await pending('burn')).toHaveLength(1);
    await syncLocalNotifications(FLAT, settings, WARN_AT + 31 * MIN);
    expect(await pending('burn')).toHaveLength(0);
  });
});
