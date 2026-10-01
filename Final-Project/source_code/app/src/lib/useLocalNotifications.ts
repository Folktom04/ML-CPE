/**
 * Keeps the scheduled local notifications in line with the latest forecast and settings (day 22).
 * Runs whenever the home screen has a new forecast or a relevant setting changes; each run
 * replaces the future notifications of every kind it manages.
 *
 * Day 23: while server push is active (`pushActive`, see push.ts) the server sends "UV สูง" /
 * "ปลอดภัยแล้ว", so those two kinds are not scheduled here (no double alerts); the daily
 * summary, burn-dose warning and reapply reminder stay local.
 */

import { useEffect } from 'react';

import type { HourUV } from '@/api/types';
import { DEFAULT_SKIN_TYPE } from '@/config';
import { burnNotification, planDaily, planReapply, planUvAlerts } from '@/lib/alertPlan';
import { sunStatus } from '@/lib/dose';
import {
  loadHistory,
  notificationsAvailable,
  replaceScheduled,
  saveHistory,
} from '@/lib/notifications';
import type { Settings } from '@/lib/settings';
import type { SkinType } from '@/lib/skinQuiz';

/** Plan and schedule every local notification for `hours` (exported for tests). */
export async function syncLocalNotifications(
  hours: HourUV[],
  s: Settings,
  nowMs: number = Date.now(),
  pushActive = false,
): Promise<void> {
  if (!notificationsAvailable()) return; // Expo Go on Android / web: nothing to schedule
  const skin = (s.skinType ?? DEFAULT_SKIN_TYPE) as SkinType;
  const history = await loadHistory(nowMs);
  const uv =
    s.notifyEnabled && !pushActive
      ? planUvAlerts(hours, nowMs, { threshold: s.alertThreshold, skin }, history)
    : [];
  await replaceScheduled(['uv_high', 'uv_safe'], uv, nowMs);
  await saveHistory(history, uv);

  const daily = s.dailySummary ? planDaily(hours, nowMs, { threshold: s.alertThreshold }) : [];
  await replaceScheduled(['daily_summary', 'daily_fallback'], daily, nowMs);

  const warnAt = s.sunStartedAt ? sunStatus(hours, skin, s.sunStartedAt, nowMs).warnAt : null;
  await replaceScheduled(['burn'], warnAt ? [burnNotification(warnAt)] : [], nowMs);

  const reapply =
    s.reapplyReminder && s.reapplyAt && s.reapplyAt > nowMs
      ? planReapply(hours, s.reapplyAt - 2 * 3600 * 1000).plan
      : null;
  await replaceScheduled(['reapply'], reapply ? [reapply] : [], nowMs);
}

export function useLocalNotifications(
  hours: HourUV[] | null,
  s: Settings,
  pushActive = false,
): void {
  useEffect(() => {
    if (!hours || !notificationsAvailable()) return;
    syncLocalNotifications(hours, s, Date.now(), pushActive).catch(() => {
      // notifications are extra; the screen keeps working without them
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only these settings matter here
  }, [
    hours,
    s.notifyEnabled,
    s.alertThreshold,
    s.dailySummary,
    s.reapplyReminder,
    s.skinType,
    s.sunStartedAt,
    s.reapplyAt,
    pushActive,
  ]);
}
