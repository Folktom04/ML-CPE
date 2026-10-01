/**
 * Server push (day 23): the phone's Expo push token and whether server push is active.
 *
 * The server sends only "UV สูง" and "ปลอดภัยแล้ว", for the user's province, and only for users
 * who gave consent. While server push is active the app does not schedule those two kinds as
 * local notifications (no double alerts); the daily summary, burn-dose warning and reapply
 * reminder stay local. `pushActive` is never stored: it starts false on every app start and is
 * true only when (a) consent, skin type, province, alerts on and a server user are set,
 * (b) the latest settings reached the server (`serverPending` false), (c) this phone and build
 * give an Expo push token, (d) `PUT /users/{id}/push-token` answers 200 and (e) `/health` says
 * `push_scheduler: true`. Otherwise every alert stays local, as on day 22.
 *
 * expo-notifications is reached only through `loadNotifications()` (see notifications.ts): it
 * throws at import in Expo Go on Android, where remote push is unavailable since SDK 53 anyway
 * (checked for SDK 57 on 29 Sep 2026, https://docs.expo.dev/versions/latest/sdk/notifications/).
 * Limitation: this is checked when the app opens; if the server stops later, no push arrives
 * (and no local "UV สูง" was scheduled) until the app is opened again.
 */

import Constants from 'expo-constants';
import * as Device from 'expo-device';
import type * as NotificationsModule from 'expo-notifications';
import { Platform } from 'react-native';

import { loadNotifications } from '@/lib/notifications';
import type { Settings } from '@/lib/settings';

export type PushEnv = {
  os: string;
  isDevice: boolean;
  /** 'storeClient' = Expo Go; 'standalone' / 'bare' = a build. */
  executionEnvironment: string | null;
  /** EAS project id (`extra.eas.projectId`, written by `eas init`); null until set up. */
  projectId: string | null;
};

type TokenApi = Pick<typeof NotificationsModule, 'getPermissionsAsync' | 'getExpoPushTokenAsync'>;

/** What this phone and build can do (from expo-device / expo-constants). */
export function currentPushEnv(): PushEnv {
  const extra = Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined;
  return {
    os: Platform.OS,
    isDevice: Device.isDevice,
    executionEnvironment: (Constants.executionEnvironment as string | undefined) ?? null,
    projectId: extra?.eas?.projectId ?? Constants.easConfig?.projectId ?? null,
  };
}

/** Why this phone/build cannot get a push token, or null when it can. */
export function pushUnavailableReason(env: PushEnv): string | null {
  if (env.os !== 'android' && env.os !== 'ios') return 'web';
  if (!env.isDevice) return 'simulator';
  if (env.os === 'android' && env.executionEnvironment === 'storeClient') return 'expo-go-android';
  if (!env.projectId) return 'no-project-id';
  return null;
}

/**
 * The Expo push token, or null (web, simulator, Expo Go on Android, no EAS project id, no
 * notifications module, no permission, or any error). Never asks for permission and never throws.
 */
export async function getPushToken(
  env: PushEnv = currentPushEnv(),
  api: TokenApi | null = null,
): Promise<string | null> {
  if (pushUnavailableReason(env)) return null;
  const n = api ?? loadNotifications().mod;
  if (!n) return null;
  try {
    if (!(await n.getPermissionsAsync()).granted) return null;
    const { data } = await n.getExpoPushTokenAsync({ projectId: env.projectId! });
    return typeof data === 'string' && data.startsWith('ExponentPushToken[') ? data : null;
  } catch {
    return null;
  }
}

export type PushDeps = {
  getToken: () => Promise<string | null>;
  register: (userId: number, deviceId: string, token: string, platform: string) => Promise<unknown>;
  health: () => Promise<{ status?: string; push_scheduler?: boolean }>;
  platform: string;
};

/** Conditions (a) and (b): settings that allow server push at all. */
export function pushEligible(s: Settings): boolean {
  return (
    s.serverConsent &&
    s.skinType !== null &&
    s.province !== null &&
    s.notifyEnabled &&
    s.userId !== null &&
    s.deviceId !== null &&
    !s.serverPending
  );
}

/**
 * Whether server push is active: (a)+(b) eligible settings, (c) a token, (d) the token
 * registered and (e) the server's push scheduler running. Any failure gives false, so the app
 * keeps its local alerts. The token is never registered without consent.
 */
export async function checkServerPush(s: Settings, deps: PushDeps): Promise<boolean> {
  if (!pushEligible(s)) return false;
  try {
    const token = await deps.getToken();
    if (!token) return false;
    await deps.register(s.userId!, s.deviceId!, token, deps.platform);
    const h = await deps.health();
    return h?.push_scheduler === true;
  } catch {
    return false;
  }
}
