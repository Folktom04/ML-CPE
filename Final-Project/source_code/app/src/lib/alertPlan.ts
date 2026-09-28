/**
 * Plans local notifications from the hourly forecast (day 22). Pure functions: the scheduler in
 * `notifications.ts` only turns the plan into OS notifications.
 *
 * - UV alert: at the start of a daytime hour whose alert_uvi reaches the threshold
 *   (`reachesAlert`, WHO rounding), "safe again" when it falls below threshold − 2
 *   (`isSafeAgain`, hysteresis), at most one of each kind per 3 h, none at night.
 * - Daily summary at 07:00 (Asia/Bangkok) from that day's forecast; for days the forecast does not
 *   cover, a generic "open the app" reminder instead.
 * - Reapply sunscreen 2 h after "applied", unless that is at night.
 * Every text says "ประมาณ": the values are estimates.
 */

import type { HourUV } from '@/api/types';
import { BURN_FRACTION, hourStartMs } from '@/lib/dose';
import { burnMinutesAt, type SkinType } from '@/lib/skinQuiz';
import { formatClock, formatHourInterval, isSafeAgain, levelIndex, reachesAlert, WHO_LEVELS } from '@/lib/uv';

export type NotificationKind =
  | 'uv_high'
  | 'uv_safe'
  | 'daily_summary'
  | 'daily_fallback'
  | 'burn'
  | 'reapply';

export type PlannedNotification = {
  kind: NotificationKind;
  /** Delivery time, ms since epoch. */
  at: number;
  title: string;
  body: string;
};

/** A UV alert that was scheduled for a time that has already passed (treated as sent). */
export type PastEvent = { kind: 'uv_high' | 'uv_safe'; at: number };

export const COOLDOWN_MS = 3 * 3600 * 1000;
export const REAPPLY_MS = 2 * 3600 * 1000;
export const SUMMARY_HOUR_BKK = 7;
export const FALLBACK_DAYS = 7;
const DAY_MS = 24 * 3600 * 1000;
const BKK_OFFSET_MS = 7 * 3600 * 1000;
/** An hour that starts sooner than this is "now": shown on screen, not notified. */
const MIN_LEAD_MS = 60 * 1000;

const safeText = (h: HourUV) => `ค่าประมาณ UVI ${h.uvi.toFixed(1)} (ค่าบน ${h.alert_uvi.toFixed(1)})`;

/** UV alerts ("UV สูง" / "ปลอดภัยแล้ว") for the forecast hours after `nowMs`. */
export function planUvAlerts(
  hours: HourUV[],
  nowMs: number,
  opts: { threshold: number; skin: SkinType },
  history: PastEvent[] = [],
): PlannedNotification[] {
  const { threshold, skin } = opts;
  const safe = threshold - 2;
  const last: Record<PastEvent['kind'], number> = { uv_high: -Infinity, uv_safe: -Infinity };
  for (const e of history) if (e.at <= nowMs) last[e.kind] = Math.max(last[e.kind], e.at);

  // Initial state from the hour we are in (it is on the screen) and the last alert sent.
  const current = hours.find((h) => hourStartMs(h) <= nowMs && nowMs < hourStartMs(h) + 3600e3);
  let alerted = false;
  if (current?.is_daylight) {
    alerted =
      reachesAlert(current.alert_uvi, threshold) ||
      (last.uv_high > last.uv_safe &&
        nowMs - last.uv_high < 12 * 3600e3 &&
        !isSafeAgain(current.alert_uvi, safe));
  }

  const out: PlannedNotification[] = [];
  for (const h of hours) {
    const t = hourStartMs(h);
    if (t < nowMs + MIN_LEAD_MS) continue;
    if (!h.is_daylight) {
      alerted = false; // no alerts at night; the next day starts fresh
      continue;
    }
    if (!alerted && reachesAlert(h.alert_uvi, threshold)) {
      alerted = true;
      if (t - last.uv_high >= COOLDOWN_MS) {
        const level = WHO_LEVELS[levelIndex(h.alert_uvi)];
        out.push({
          kind: 'uv_high',
          at: t,
          title: `UV ${level} ช่วง ${formatHourInterval(h.time)}`,
          body:
            `${safeText(h)} · ผิวประเภท ${skin} อาจไหม้ในประมาณ ` +
            `${burnMinutesAt(skin, h.alert_uvi)} นาทีถ้าอยู่กลางแดด · ทาครีมกันแดดและหาที่ร่ม`,
        });
        last.uv_high = t;
      }
    } else if (alerted && isSafeAgain(h.alert_uvi, safe)) {
      alerted = false;
      if (t - last.uv_safe >= COOLDOWN_MS) {
        out.push({
          kind: 'uv_safe',
          at: t,
          title: `UV ลดลงแล้ว ตั้งแต่ ${formatClock(h.time)}`,
          body: `${safeText(h)} ต่ำกว่า ${safe} แล้ว`,
        });
        last.uv_safe = t;
      }
    }
  }
  return out;
}

/** Next 07:00 Asia/Bangkok strictly after `nowMs`. */
export function nextSummaryTime(nowMs: number): number {
  const local = nowMs + BKK_OFFSET_MS;
  const dayStart = Math.floor(local / DAY_MS) * DAY_MS;
  let t = dayStart + SUMMARY_HOUR_BKK * 3600e3 - BKK_OFFSET_MS;
  if (t <= nowMs) t += DAY_MS;
  return t;
}

/** "YYYY-MM-DD" of a time in Asia/Bangkok. */
function bkkDate(ms: number): string {
  return new Date(ms + BKK_OFFSET_MS).toISOString().slice(0, 10);
}

/**
 * Daily 07:00 notifications from the next one onward: a summary for each day the forecast covers
 * (its daytime hours), and a generic "open the app" reminder for the following days up to
 * FALLBACK_DAYS ahead.
 */
export function planDaily(
  hours: HourUV[],
  nowMs: number,
  opts: { threshold: number },
): PlannedNotification[] {
  const out: PlannedNotification[] = [];
  const first = nextSummaryTime(nowMs);
  for (let d = 0; d < FALLBACK_DAYS; d += 1) {
    const at = first + d * DAY_MS;
    const date = bkkDate(at);
    const day = hours.filter((h) => h.is_daylight && h.time.slice(0, 10) === date);
    // a summary needs the whole daytime of that day, not only its first hours
    const complete = day.length > 0 && hours.some((h) => h.time.slice(0, 10) > date);
    if (complete) {
      const peak = day.reduce((b, h) => (h.alert_uvi > b.alert_uvi ? h : b));
      const high = day.filter((h) => reachesAlert(h.alert_uvi, opts.threshold));
      const when = high.length
        ? `ช่วงที่ถึงเกณฑ์เตือน ${formatClock(high[0].time)}–${formatHourInterval(high[high.length - 1].time).slice(6)}`
        : 'ไม่ถึงเกณฑ์เตือน';
      out.push({
        kind: 'daily_summary',
        at,
        title: `UV วันนี้สูงสุดประมาณ ${peak.uvi.toFixed(1)} (${peak.level})`,
        body: `ราว ${formatClock(peak.time)} (ค่าบนประมาณ ${peak.alert_uvi.toFixed(1)}) · ${when}`,
      });
    } else {
      out.push({
        kind: 'daily_fallback',
        at,
        title: 'เปิดแอปเพื่อดู UV วันนี้',
        body: 'ยังไม่มีพยากรณ์ของวันนี้ในเครื่อง เปิดแอปเพื่อดูค่า UV โดยประมาณและตั้งการเตือนใหม่',
      });
    }
  }
  return out;
}

/** Reapply reminder 2 h after `appliedMs`, or null (with a reason) if that is at night. */
export function planReapply(
  hours: HourUV[],
  appliedMs: number,
): { plan: PlannedNotification | null; reason: string | null } {
  const at = appliedMs + REAPPLY_MS;
  const h = hours.find((x) => hourStartMs(x) <= at && at < hourStartMs(x) + 3600e3);
  if (h && !h.is_daylight) {
    return { plan: null, reason: 'อีก 2 ชม. จะเป็นช่วงไม่มีแดดแล้ว จึงไม่ตั้งเตือนทาซ้ำ' };
  }
  return {
    plan: {
      kind: 'reapply',
      at,
      title: 'ถึงเวลาทาครีมกันแดดซ้ำ',
      body: 'ทาครีมไปแล้วประมาณ 2 ชั่วโมง ถ้ายังอยู่กลางแจ้งควรทาซ้ำ โดยเฉพาะหลังเหงื่อออกหรือโดนน้ำ',
    },
    reason: null,
  };
}

/** The burn warning of a "going out" session (time from `sunStatus().warnAt`). */
export function burnNotification(warnAt: number): PlannedNotification {
  return {
    kind: 'burn',
    at: warnAt,
    title: 'ใกล้ถึงเวลาผิวไหม้ (ประมาณ)',
    body:
      `ได้รับ UV ประมาณ ${Math.round(BURN_FRACTION * 100)} % ของปริมาณที่ทำให้ผิวแดงแล้ว ` +
      '(คิดแบบอยู่กลางแดดเต็มที่) ควรเข้าร่ม สวมเสื้อแขนยาว หรือทาครีมกันแดด',
  };
}
