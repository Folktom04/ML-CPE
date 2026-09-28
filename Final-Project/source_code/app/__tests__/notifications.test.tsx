import AsyncStorage from '@react-native-async-storage/async-storage';
import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { SunSessionCard } from '@/components/SunSessionCard';
import type { PlannedNotification } from '@/lib/alertPlan';
import {
  clearAllNotifications,
  HISTORY_KEY,
  loadHistory,
  notificationPermission,
  replaceScheduled,
  saveHistory,
} from '@/lib/notifications';
import { DEFAULT_SETTINGS, type Settings } from '@/lib/settings';
import { syncLocalNotifications } from '@/lib/useLocalNotifications';

import { mkHours } from './fixtures';
import { MemoryStorage, renderWithSettings } from './helpers';

const N = jest.requireMock('expo-notifications');
const at = (iso: string) => Date.parse(iso);
const NOW = at('2026-09-29T05:30:00+07:00');
// 05:00-20:00 on 29 Sep, then night until 30 Sep 04:00
const HOURS = mkHours('2026-09-29T05:00:00+07:00', [
  0, 0.6, 2, 4, 6, 7.5, 9, 10, 10.2, 9.5, 7, 5.9, 4, 2, 0.8, 0, 0, 0, 0, 0, 0, 0, 0, 0,
]);

async function scheduled() {
  const all = await N.getAllScheduledNotificationsAsync();
  return all.map((n: { content: { data: { kind: string }; title: string; body: string } }) => ({
    kind: n.content.data.kind,
    text: `${n.content.title} ${n.content.body}`,
  }));
}

const plan = (kind: PlannedNotification['kind'], iso: string): PlannedNotification => ({
  kind,
  at: at(iso),
  title: kind,
  body: 'ประมาณ',
});

beforeEach(async () => {
  N.__reset();
  jest.clearAllMocks();
  N.getPermissionsAsync.mockResolvedValue({ granted: true, canAskAgain: true });
  await AsyncStorage.clear();
});

describe('scheduler', () => {
  it('replaces only the given kinds and only future times, as DATE triggers', async () => {
    await replaceScheduled(['daily_summary'], [plan('daily_summary', '2026-09-30T07:00:00+07:00')], NOW);
    const n = await replaceScheduled(
      ['uv_high', 'uv_safe'],
      [
        plan('uv_high', '2026-09-29T05:00:00+07:00'), // past: skipped
        plan('uv_high', '2026-09-29T10:00:00+07:00'),
        plan('uv_safe', '2026-09-29T17:00:00+07:00'),
      ],
      NOW,
    );
    expect(n).toBe(2);
    const req = N.scheduleNotificationAsync.mock.calls[1][0];
    expect(req.trigger).toEqual({
      type: 'date',
      date: at('2026-09-29T10:00:00+07:00'),
      channelId: 'uv-alerts',
    });
    await replaceScheduled(['uv_high', 'uv_safe'], [], NOW); // e.g. alerts switched off
    expect((await scheduled()).map((s: { kind: string }) => s.kind)).toEqual(['daily_summary']);
  });

  it('schedules nothing without permission, and asks only when told to', async () => {
    N.getPermissionsAsync.mockResolvedValue({ granted: false, canAskAgain: true });
    N.requestPermissionsAsync.mockResolvedValueOnce({ granted: false });
    expect(await replaceScheduled(['uv_high'], [plan('uv_high', '2026-09-29T10:00:00+07:00')], NOW)).toBe(0);
    expect(N.requestPermissionsAsync).not.toHaveBeenCalled();
    expect(await notificationPermission(true)).toBe(false);
    expect(N.requestPermissionsAsync).toHaveBeenCalledTimes(1);
    // Android channels are created before asking (Jest runs as iOS, which has none)
  });

  it('history keeps past UV alerts for 24 h (cooldown across app openings)', async () => {
    await saveHistory(
      [{ kind: 'uv_high', at: at('2026-09-28T04:00:00+07:00') }],
      [plan('uv_high', '2026-09-29T10:00:00+07:00'), plan('daily_summary', '2026-09-30T07:00:00+07:00')],
    );
    expect(await loadHistory(at('2026-09-29T09:00:00+07:00'))).toEqual([]);
    expect(await loadHistory(at('2026-09-29T11:00:00+07:00'))).toEqual([
      { kind: 'uv_high', at: at('2026-09-29T10:00:00+07:00') },
    ]);
    await AsyncStorage.setItem(HISTORY_KEY, '{broken');
    expect(await loadHistory(NOW)).toEqual([]);
  });

  it('"delete my data" clears every scheduled notification and the history', async () => {
    await replaceScheduled(['reapply'], [plan('reapply', '2026-09-29T12:00:00+07:00')], NOW);
    await saveHistory([], [plan('uv_high', '2026-09-29T05:00:00+07:00')]);
    await clearAllNotifications();
    expect(await scheduled()).toEqual([]);
    expect(await AsyncStorage.getItem(HISTORY_KEY)).toBeNull();
  });
});

describe('syncLocalNotifications', () => {
  const s = (patch: Partial<Settings> = {}): Settings => ({
    ...DEFAULT_SETTINGS,
    skinType: 'III',
    ...patch,
  });

  it('UV alerts + daily summary/fallback, every text says "ประมาณ"', async () => {
    await syncLocalNotifications(HOURS, s(), NOW);
    const all = await scheduled();
    const kinds = all.map((x: { kind: string }) => x.kind);
    expect(kinds.filter((k: string) => k === 'uv_high')).toHaveLength(1);
    expect(kinds.filter((k: string) => k === 'uv_safe')).toHaveLength(1);
    expect(kinds.filter((k: string) => k.startsWith('daily'))).toHaveLength(7);
    expect(all.every((x: { text: string }) => x.text.includes('ประมาณ'))).toBe(true);
  });

  it('respects the switches, and a reapply/burn from the saved session', async () => {
    await syncLocalNotifications(
      HOURS,
      s({
        notifyEnabled: false,
        dailySummary: false,
        sunStartedAt: at('2026-09-29T10:00:00+07:00'),
        reapplyAt: at('2026-09-29T12:00:00+07:00'),
      }),
      at('2026-09-29T10:05:00+07:00'),
    );
    const kinds = (await scheduled()).map((x: { kind: string }) => x.kind).sort();
    expect(kinds).toEqual(['burn', 'reapply']);
    await syncLocalNotifications(HOURS, s({ reapplyReminder: false }), NOW);
    expect((await scheduled()).map((x: { kind: string }) => x.kind)).not.toContain('reapply');
  });
});

describe('SunSessionCard', () => {
  const DAY_NOW = at('2026-09-29T11:00:00+07:00');

  it('"ออกแดด" starts a session with the 80 % warning time and the full-sun caveat', async () => {
    const storage = new MemoryStorage({ skinType: 'III' });
    await renderWithSettings(
      <SunSessionCard hours={HOURS} skin="III" isDaylight nowMs={DAY_NOW} />,
      storage,
    );
    expect(screen.getByTestId('sun-hint')).toHaveTextContent(/อยู่กลางแดดเต็มที่/);
    expect(screen.getByTestId('sun-hint')).toHaveTextContent(/เวลาจริงจะนานกว่านี้/);
    await fireEvent.press(await screen.findByTestId('sun-start'));
    await waitFor(() => expect(storage.stored()?.sunStartedAt).toBe(DAY_NOW));
    // alert_uvi 9 at 11:00 -> 280 J/m2 / 0.225 W = 1244 s -> 11:20
    expect(screen.getByTestId('sun-warn-at')).toHaveTextContent('จะเตือนราว 11:20 (ที่ประมาณ 80 % ของ MED)');
    await fireEvent.press(screen.getByTestId('sun-stop'));
    await waitFor(() => expect(storage.stored()?.sunStartedAt).toBeNull());
  });

  it('"ทาครีมแล้ว" sets the reminder 2 h later, but not into the night', async () => {
    const storage = new MemoryStorage({ skinType: 'III' });
    await renderWithSettings(
      <SunSessionCard hours={HOURS} skin="III" isDaylight nowMs={DAY_NOW} />,
      storage,
    );
    await fireEvent.press(await screen.findByTestId('reapply-start'));
    await waitFor(() => expect(storage.stored()?.reapplyAt).toBe(at('2026-09-29T13:00:00+07:00')));
    expect(screen.getByTestId('reapply-at')).toHaveTextContent('จะเตือนทาครีมซ้ำราว 13:00');
  });

  it('at dusk the reapply reminder is refused with a reason', async () => {
    const storage = new MemoryStorage({ skinType: 'III' });
    await renderWithSettings(
      <SunSessionCard hours={HOURS} skin="III" isDaylight nowMs={at('2026-09-29T18:30:00+07:00')} />,
      storage,
    );
    await fireEvent.press(await screen.findByTestId('reapply-start'));
    expect(await screen.findByTestId('reapply-reason')).toHaveTextContent(/ไม่มีแดด/);
    expect(storage.stored()?.reapplyAt ?? null).toBeNull();
  });

  it('at night with no session the card is hidden', async () => {
    await renderWithSettings(
      <SunSessionCard hours={HOURS} skin="III" isDaylight={false} nowMs={at('2026-09-29T21:00:00+07:00')} />,
    );
    expect(screen.queryByTestId('sun-start')).toBeNull();
    expect(screen.queryByTestId('sun-hint')).toBeNull();
  });

  it('without notification permission it still works and says so', async () => {
    N.getPermissionsAsync.mockResolvedValue({ granted: false, canAskAgain: false });
    await renderWithSettings(
      <SunSessionCard hours={HOURS} skin="III" isDaylight nowMs={DAY_NOW} />,
      new MemoryStorage({ skinType: 'III' }),
    );
    expect(await screen.findByTestId('notify-not-allowed')).toBeTruthy();
    expect(screen.getByTestId('sun-start')).toBeTruthy();
  });
});
