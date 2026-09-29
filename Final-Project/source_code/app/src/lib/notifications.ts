/**
 * Local notifications with expo-notifications (day 22), loaded lazily through this ONE wrapper.
 *
 * This is the only file that may load `expo-notifications` (a test checks it); other files use
 * `import type` at most. The package cannot even be imported in Expo Go on Android: in 57.0.21
 * `index.js` re-exports `DevicePushTokenAutoRegistration.fx.js`, whose module-level code calls
 * `addPushTokenListener`, which throws "…removed from Expo Go with the release of SDK 53" on
 * Android (CHANGELOG 55.0.0: "throw instead of logging a warning"). A static import therefore
 * crashed the whole app from `_layout`. So `loadNotifications()` does not require the module in
 * Expo Go on Android or on the web, wraps the require in try/catch otherwise, and caches the
 * result. Without the module every function here does nothing and the screens say why; the rest
 * of the app works. A development build is needed for notifications on Android.
 *
 * Each scheduled notification carries `data.kind`, so one kind can be replaced without touching
 * the others. Nothing leaves the phone, so no consent is needed. Android may deliver a scheduled
 * notification later than its time (Doze / battery saving); see the phone-test steps.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import type * as NotificationsModule from 'expo-notifications';
import { Platform } from 'react-native';

import type { NotificationKind, PastEvent, PlannedNotification } from '@/lib/alertPlan';

export const HISTORY_KEY = 'uvguard.notify-history.v1';
const HISTORY_KEEP_MS = 24 * 3600 * 1000;
const CHANNEL_ALERTS = 'uv-alerts';
const CHANNEL_REMINDERS = 'reminders';
const ALERT_KINDS: NotificationKind[] = ['uv_high', 'uv_safe', 'burn'];

type Module = typeof NotificationsModule;
export type NotifyUnavailableReason = 'web' | 'expo-go-android' | 'load-failed';
export type LoadedNotifications = { mod: Module | null; reason: NotifyUnavailableReason | null };
export type NotifyEnv = { os: string; executionEnvironment: string | null };

/** Why there are no notifications, shown on the screens (nothing is shown on the web). */
export const NOTIFY_UNAVAILABLE_TH: Record<Exclude<NotifyUnavailableReason, 'web'>, string> = {
  'expo-go-android':
    'Expo Go บน Android ไม่รองรับการแจ้งเตือน (ถูกถอดออกตั้งแต่ SDK 53) จึงไม่มีแจ้งเตือนเด้งขึ้นมา ' +
    'ต้องใช้ development build',
  'load-failed': 'โหลดระบบแจ้งเตือนของเครื่องไม่สำเร็จ จึงไม่มีแจ้งเตือนเด้งขึ้นมา',
};

/** What still works without notifications (matches SunSessionCard: % of MED and the 80 % time). */
export const WITHOUT_NOTIFY_TH =
  'ยังดูค่า UV และพยากรณ์รายชั่วโมงได้ตามปกติ ปุ่ม "ออกแดด" แสดงบนจอว่าได้รับ UV ไปกี่ % ของ MED ' +
  'และจะถึง 80 % ราวกี่โมง แต่ต้องเปิดแอปดูเอง';

let loaded: LoadedNotifications | null = null;
let setUp = false;

/** Platform and Expo Go / build of this app (expo-constants is safe to import everywhere). */
function currentEnv(): NotifyEnv {
  return {
    os: Platform.OS,
    executionEnvironment: (Constants.executionEnvironment as string | undefined) ?? null,
  };
}

/** The one place that requires the package (lazy on purpose, see the top of this file). */
function requireExpoNotifications(): Module {
  // eslint-disable-next-line @typescript-eslint/no-require-imports -- lazy on purpose
  return require('expo-notifications') as Module;
}

/**
 * Load expo-notifications once: never on the web or in Expo Go on Android (it throws there at
 * import), and inside try/catch elsewhere. `env` and `requireModule` are for tests; the result
 * is cached.
 */
export function loadNotifications(
  env: NotifyEnv = currentEnv(),
  requireModule: () => Module = requireExpoNotifications,
): LoadedNotifications {
  if (loaded) return loaded;
  if (env.os !== 'android' && env.os !== 'ios') {
    loaded = { mod: null, reason: 'web' };
  } else if (env.os === 'android' && env.executionEnvironment === 'storeClient') {
    loaded = { mod: null, reason: 'expo-go-android' };
  } else {
    try {
      loaded = { mod: requireModule(), reason: null };
    } catch {
      loaded = { mod: null, reason: 'load-failed' };
    }
  }
  return loaded;
}

/** Whether local notifications can be used on this phone and build. */
export function notificationsAvailable(): boolean {
  return loadNotifications().mod !== null;
}

/** Why notifications are unavailable (null when available). */
export function notificationsUnavailableReason(): NotifyUnavailableReason | null {
  return loadNotifications().reason;
}

/** Thai reason to show on screen, or null (available, or the web build). */
export function notifyUnavailableText(): string | null {
  const r = notificationsUnavailableReason();
  return r && r !== 'web' ? NOTIFY_UNAVAILABLE_TH[r] : null;
}

/** Tests only: forget the cached load, or force a result. */
export function resetNotificationsForTests(forced: LoadedNotifications | null = null): void {
  loaded = forced;
  setUp = false;
}

/** Foreground display + Android channels (a channel must exist before the permission prompt). */
export async function setupNotifications(): Promise<void> {
  const Notifications = loadNotifications().mod;
  if (!Notifications || setUp) return;
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
  const Notifications = loadNotifications().mod;
  if (!Notifications) return false;
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
  const Notifications = loadNotifications().mod;
  if (!Notifications) return;
  const all = await Notifications.getAllScheduledNotificationsAsync();
  await Promise.all(
    all
      .filter((n) => kinds.includes(n.content.data?.kind as NotificationKind))
      .map((n) => Notifications.cancelScheduledNotificationAsync(n.identifier)),
  );
}

/**
 * Replace the scheduled notifications of `kinds` with `plan` (only future times are scheduled).
 * Returns how many were scheduled; 0 without permission, on the web or without the module.
 */
export async function replaceScheduled(
  kinds: NotificationKind[],
  plan: PlannedNotification[],
  nowMs: number = Date.now(),
): Promise<number> {
  const Notifications = loadNotifications().mod;
  if (!Notifications) return 0;
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
  const Notifications = loadNotifications().mod;
  if (Notifications) await Notifications.cancelAllScheduledNotificationsAsync();
  try {
    await AsyncStorage.removeItem(HISTORY_KEY);
  } catch {
    // nothing to clear
  }
}
