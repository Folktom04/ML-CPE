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
  // An overdue notification (time passed, Android not delivered yet) is kept while its reason
  // still holds, see replaceScheduled(); switching a kind off or ending a session cancels it.
  const uvOn = s.notifyEnabled && !pushActive;
  const uv = uvOn
    ? planUvAlerts(hours, nowMs, { threshold: s.alertThreshold, skin }, history)
    : [];
  await replaceScheduled(['uv_high', 'uv_safe'], uv, nowMs, () => uvOn);
  await saveHistory(history, uv);

  const daily = s.dailySummary ? planDaily(hours, nowMs, { threshold: s.alertThreshold }) : [];
  await replaceScheduled(['daily_summary', 'daily_fallback'], daily, nowMs, () => s.dailySummary);

  const started = s.sunStartedAt;
  const warnAt = started ? sunStatus(hours, skin, started, nowMs).warnAt : null;
  // keep the overdue warning of THIS session only (a new "ออกแดด" starts after it), unless a
  // newer forecast moved the 80 % time into the future (then the new warning replaces it)
  await replaceScheduled(['burn'], warnAt ? [burnNotification(warnAt)] : [], nowMs, (n) =>
    started !== null && n.at >= started ? warnAt === null || warnAt <= nowMs : false,
  );

  const reapplyAt = s.reapplyReminder ? s.reapplyAt : null;
  const reapply =
    reapplyAt && reapplyAt > nowMs ? planReapply(hours, reapplyAt - 2 * 3600 * 1000).plan : null;
  // keep only the overdue reminder of the current press ("ทาครีมอีกครั้งแล้ว" moves reapplyAt)
  await replaceScheduled(['reapply'], reapply ? [reapply] : [], nowMs, (n) =>
    reapplyAt ? Math.abs(n.at - reapplyAt) < 60 * 1000 : false,
  );
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
