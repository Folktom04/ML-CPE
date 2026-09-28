/**
 * User settings kept on the phone (day 19), stored as JSON in AsyncStorage.
 *
 * `skinType`, `notifyEnabled`, `alertThreshold` and `alertBurnMinutes` are sent to the server
 * (`POST /users`, `PUT /users/{id}/settings`) for remote alerts (day 23) ONLY after the user
 * turns on `serverConsent` (explicit, opt-in: the skin type is health-related data, PDPA s.26,
 * see docs/db.md). Turning it off withdraws consent and deletes the server record. The daily
 * summary and sunscreen reminder are local notifications (day 22) and stay on the phone.
 * `deviceId` is a random UUID that proves ownership of the server record (X-Device-Id).
 */

import { isSkinType, type SkinType } from '@/lib/skinQuiz';

export const STORAGE_KEY = 'uvguard.settings.v1';

/** Alert levels offered in the app (WHO lower bounds of สูง, สูงมาก, รุนแรงมาก). */
export const ALERT_THRESHOLDS = [6, 8, 11] as const;
export type AlertThreshold = (typeof ALERT_THRESHOLDS)[number];

/** Warn when this many minutes are left before a burn. */
export const BURN_MINUTE_OPTIONS = [15, 30, 60] as const;
export type BurnMinutes = (typeof BURN_MINUTE_OPTIONS)[number];

/** Hysteresis gap: "safe again" is sent below alert − 2 (6→4, 8→6, 11→9); same as the API. */
export const SAFE_GAP = 2;

export type Settings = {
  /** null until the quiz is done or a type is picked. */
  skinType: SkinType | null;
  notifyEnabled: boolean;
  alertThreshold: AlertThreshold;
  alertBurnMinutes: BurnMinutes;
  dailySummary: boolean;
  reapplyReminder: boolean;
  /** Explicit consent to send the skin type and alert settings to the server (default off). */
  serverConsent: boolean;
  deviceId: string | null;
  userId: number | null;
  /** The user acknowledged the sky-photo privacy notice (day 20; phone only, never sent). */
  skyNoticeAck: boolean;
};

export const DEFAULT_SETTINGS: Settings = {
  skinType: null,
  notifyEnabled: true,
  alertThreshold: 8,
  alertBurnMinutes: 30,
  dailySummary: true,
  reapplyReminder: true,
  serverConsent: false,
  deviceId: null,
  userId: null,
  skyNoticeAck: false,
};

/** "Safe again" UVI for an alert UVI. */
export function safeThresholdFor(alert: number): number {
  return alert - SAFE_GAP;
}

/** The fields the server stores, in the API's names. */
export function serverSettings(s: Settings) {
  return {
    skin_type: s.skinType,
    notify_enabled: s.notifyEnabled,
    alert_threshold: s.alertThreshold,
    alert_burn_minutes: s.alertBurnMinutes,
  };
}

function pick<T>(value: unknown, ok: (v: unknown) => boolean, fallback: T): T {
  return ok(value) ? (value as T) : fallback;
}

const isBool = (v: unknown) => typeof v === 'boolean';

/**
 * Settings from stored JSON. Unknown or damaged fields fall back to the defaults one by one,
 * and unreadable JSON gives the defaults.
 */
export function parseSettings(raw: string | null): Settings {
  if (!raw) return { ...DEFAULT_SETTINGS };
  let obj: Record<string, unknown>;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { ...DEFAULT_SETTINGS };
    }
    obj = parsed;
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
  const d = DEFAULT_SETTINGS;
  return {
    skinType: pick(obj.skinType, isSkinType, d.skinType),
    notifyEnabled: pick(obj.notifyEnabled, isBool, d.notifyEnabled),
    alertThreshold: pick(
      obj.alertThreshold,
      (v) => (ALERT_THRESHOLDS as readonly unknown[]).includes(v),
      d.alertThreshold,
    ),
    alertBurnMinutes: pick(
      obj.alertBurnMinutes,
      (v) => (BURN_MINUTE_OPTIONS as readonly unknown[]).includes(v),
      d.alertBurnMinutes,
    ),
    dailySummary: pick(obj.dailySummary, isBool, d.dailySummary),
    reapplyReminder: pick(obj.reapplyReminder, isBool, d.reapplyReminder),
    serverConsent: pick(obj.serverConsent, (v) => v === true, d.serverConsent),
    deviceId: pick(
      obj.deviceId,
      (v) => typeof v === 'string' && /^[A-Za-z0-9-]{16,64}$/.test(v),
      d.deviceId,
    ),
    userId: pick(obj.userId, (v) => Number.isInteger(v) && (v as number) > 0, d.userId),
    skyNoticeAck: pick(obj.skyNoticeAck, (v) => v === true, d.skyNoticeAck),
  };
}

/** Minimal storage interface (AsyncStorage in the app, a fake in tests). */
export type KeyValueStorage = {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
};

/** Stored settings, or the defaults if nothing is stored or storage fails. */
export async function loadSettings(storage: KeyValueStorage): Promise<Settings> {
  try {
    return parseSettings(await storage.getItem(STORAGE_KEY));
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export async function saveSettings(storage: KeyValueStorage, s: Settings): Promise<void> {
  await storage.setItem(STORAGE_KEY, JSON.stringify(s));
}

/** Remove everything this app stored on the phone. */
export async function clearSettings(storage: KeyValueStorage): Promise<void> {
  await storage.removeItem(STORAGE_KEY);
}
