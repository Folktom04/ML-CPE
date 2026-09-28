/**
 * Local notifications with expo-notifications (day 22). Works in Expo Go on Android and iOS
 * (docs.expo.dev/versions/latest/sdk/notifications, SDK 57, checked 29 Sep 2026: "local
 * notifications" are available in Expo Go; remote push is not, on Android, since SDK 53).
 *
 * Each scheduled notification carries `data.kind`, so one kind can be replaced without touching
 * the others. Nothing leaves the phone, so no consent is needed. Android may deliver a scheduled
 * notification later than its time (Doze / battery saving); see the phone-test steps.
 * On the web build this module does nothing.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

import type { NotificationKind, PastEvent, PlannedNotification } from '@/lib/alertPlan';

export const HISTORY_KEY = 'uvguard.notify-history.v1';
const HISTORY_KEEP_MS = 24 * 3600 * 1000;
const CHANNEL_ALERTS = 'uv-alerts';
const CHANNEL_REMINDERS = 'reminders';
const ALERT_KINDS: NotificationKind[] = ['uv_high', 'uv_safe', 'burn'];

export const supported = Platform.OS === 'android' || Platform.OS === 'ios';

let setUp = false;

/** Foreground display + Android channels (a channel must exist before the permission prompt). */
export async function setupNotifications(): Promise<void> {
  if (!supported || setUp) return;
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync(CHANNEL_ALERTS, {
      name: 'เตือนระดับ UV',
      importance: Notifications.AndroidImportance.HIGH,
    });
    await Notifications.setNotificationChannelAsync(CHANNEL_REMINDERS, {
      name: 'เตือนความจำ (สรุปรายวัน, ทาครีมซ้ำ)',
      importance: Notifications.AndroidImportance.DEFAULT,
    });
  }
  setUp = true;
}

/** Whether notifications are allowed (asks once if `ask` and not decided yet). */
export async function notificationPermission(ask: boolean): Promise<boolean> {
  if (!supported) return false;
  try {
    await setupNotifications();
    const now = await Notifications.getPermissionsAsync();
    if (now.granted || !ask || !now.canAskAgain) return now.granted;
    return (await Notifications.requestPermissionsAsync()).granted;
  } catch {
    return false;
  }
}

/** Cancel the scheduled notifications of the given kinds. */
export async function cancelKinds(kinds: NotificationKind[]): Promise<void> {
  if (!supported) return;
  const all = await Notifications.getAllScheduledNotificationsAsync();
  await Promise.all(
    all
      .filter((n) => kinds.includes(n.content.data?.kind as NotificationKind))
      .map((n) => Notifications.cancelScheduledNotificationAsync(n.identifier)),
  );
}

/**
 * Replace the scheduled notifications of `kinds` with `plan` (only future times are scheduled).
 * Returns how many were scheduled; 0 without permission or on the web.
 */
export async function replaceScheduled(
  kinds: NotificationKind[],
  plan: PlannedNotification[],
  nowMs: number = Date.now(),
): Promise<number> {
  if (!supported) return 0;
  await cancelKinds(kinds);
  if (!(await notificationPermission(false))) return 0;
  const future = plan.filter((p) => kinds.includes(p.kind) && p.at > nowMs);
  for (const p of future) {
    await Notifications.scheduleNotificationAsync({
      content: { title: p.title, body: p.body, data: { kind: p.kind } },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date: p.at,
        channelId: ALERT_KINDS.includes(p.kind) ? CHANNEL_ALERTS : CHANNEL_REMINDERS,
      },
    });
  }
  return future.length;
}

/** UV alerts scheduled earlier whose time has passed (treated as sent; for the 3 h cooldown). */
export async function loadHistory(nowMs: number = Date.now()): Promise<PastEvent[]> {
  try {
    const raw = await AsyncStorage.getItem(HISTORY_KEY);
    const list = raw ? (JSON.parse(raw) as PastEvent[]) : [];
    return Array.isArray(list)
      ? list.filter((e) => e && e.at <= nowMs && nowMs - e.at < HISTORY_KEEP_MS)
      : [];
  } catch {
    return [];
  }
}

/** Remember the UV alerts just scheduled, merged with the past ones (kept for 24 h). */
export async function saveHistory(
  past: PastEvent[],
  scheduled: PlannedNotification[],
): Promise<void> {
  const events: PastEvent[] = [
    ...past,
    ...scheduled
      .filter((p) => p.kind === 'uv_high' || p.kind === 'uv_safe')
      .map((p) => ({ kind: p.kind as PastEvent['kind'], at: p.at })),
  ];
  try {
    await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(events));
  } catch {
    // history only tunes the cooldown; losing it is harmless
  }
}

/** Remove every scheduled notification and the history (used by "delete my data"). */
export async function clearAllNotifications(): Promise<void> {
  if (supported) await Notifications.cancelAllScheduledNotificationsAsync();
  try {
    await AsyncStorage.removeItem(HISTORY_KEY);
  } catch {
    // nothing to clear
  }
}
