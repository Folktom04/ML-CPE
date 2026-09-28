/**
 * WHO UV levels, colours and display formatting.
 * Levels mirror src/metrics.py (who_level): round UVI to an integer (x.5 up), then
 * 0-2 ต่ำ, 3-5 ปานกลาง, 6-7 สูง, 8-10 สูงมาก, 11+ รุนแรงมาก.
 */

import type { HourUV } from '@/api/types';

export const WHO_LEVELS = ['ต่ำ', 'ปานกลาง', 'สูง', 'สูงมาก', 'รุนแรงมาก'] as const;
export const WHO_COLORS = ['#3E9B4F', '#D9A400', '#E36B12', '#D22F3A', '#8A3FC2'] as const;
const WHO_LOWER_BOUNDS = [0, 3, 6, 8, 11];

/**
 * UVI rounded the WHO way: nearest integer, x.5 up, negative to 0. The ONE rule for levels,
 * colours and alert thresholds, same as `round_uvi` in src/metrics.py (7.8 -> 8 -> สูงมาก).
 */
export function roundUvi(uvi: number): number {
  if (!Number.isFinite(uvi)) return 0;
  return Math.floor(Math.max(uvi, 0) + 0.5);
}

/** Whether a UVI triggers the high-UV alert (same rounding as the levels; `risk.reaches_alert`). */
export function reachesAlert(uvi: number, alertThreshold: number): boolean {
  return roundUvi(uvi) >= alertThreshold;
}

/** Whether a UVI is low enough for "safe again" (`risk.is_safe_again`). */
export function isSafeAgain(uvi: number, safeThreshold: number): boolean {
  return roundUvi(uvi) < safeThreshold;
}

/** WHO level index 0-4 of a UVI value (same rounding as the API). */
export function levelIndex(uvi: number): number {
  const rounded = roundUvi(uvi);
  let idx = 0;
  WHO_LOWER_BOUNDS.forEach((lo, i) => {
    if (rounded >= lo) idx = i;
  });
  return idx;
}

/** Index of a Thai level name from the API, or -1 if unknown. */
export function levelIndexOf(level: string): number {
  return (WHO_LEVELS as readonly string[]).indexOf(level);
}

/** WHO colour of a level name; falls back to the UVI value when the name is unknown. */
export function levelColor(level: string, uvi: number): string {
  const i = levelIndexOf(level);
  return WHO_COLORS[i >= 0 ? i : levelIndex(uvi)];
}

/** Text colour readable on a level colour (dark on yellow, white otherwise). */
export function textOn(color: string): string {
  return color.toUpperCase() === WHO_COLORS[1] ? '#1F1F1F' : '#FFFFFF';
}

/** True when the alert level (from the upper quantile) is above the level shown. */
export function alertIsHigher(level: string, alertLevel: string): boolean {
  return levelIndexOf(alertLevel) > levelIndexOf(level);
}

/** Burn time in Thai. `minutes` is null when UV is too low for a meaningful burn time. */
export function formatBurn(minutes: number | null, isDaylight: boolean): string {
  if (minutes === null || !Number.isFinite(minutes)) {
    return isDaylight ? 'UV ต่ำมาก ยังไม่เสี่ยงผิวไหม้' : 'ไม่มีความเสี่ยง (กลางคืน)';
  }
  const m = Math.max(0, Math.floor(minutes));
  if (m >= 120) return 'มากกว่า 2 ชม.';
  if (m >= 60) {
    const rest = m - 60;
    return rest === 0 ? '1 ชม.' : `1 ชม. ${rest} นาที`;
  }
  return `${m} นาที`;
}

/** "HH:MM" of an API time string (already Bangkok local, e.g. 2026-09-27T13:00:00+07:00). */
export function formatClock(iso: string): string {
  const m = /T(\d{2}):(\d{2})/.exec(iso);
  return m ? `${m[1]}:${m[2]}` : iso;
}

/** "HH:MM–HH:MM" of the hourly interval that starts at `iso`. */
export function formatHourInterval(iso: string): string {
  const m = /T(\d{2}):(\d{2})/.exec(iso);
  if (!m) return iso;
  const end = (Number(m[1]) + 1) % 24;
  return `${m[1]}:${m[2]}–${String(end).padStart(2, '0')}:${m[2]}`;
}

/** "lo–hi" with one decimal. */
export function formatRange([lo, hi]: [number, number]): string {
  return `${lo.toFixed(1)}–${hi.toFixed(1)}`;
}

/** Peak hour of the next daytime period, from the hourly forecast. */
export type DayPeak = {
  time: string;
  uvi: number;
  uvi_range: [number, number];
  level: string;
  /** true when the peak is on a later local date than `nowIso`. */
  isTomorrow: boolean;
};

/**
 * Peak of the next daytime period after `nowIso`: the first run of forecast hours with
 * UVI > 0 that starts after now, and its highest hour. Null if the forecast has none.
 * Times are compared as the API's Asia/Bangkok local ISO strings.
 */
export function nextDaytimePeak(hours: HourUV[], nowIso: string): DayPeak | null {
  const now = nowIso.slice(0, 16);
  const future = hours.filter((h) => h.time.slice(0, 16) > now);
  const start = future.findIndex((h) => h.uvi > 0);
  if (start < 0) return null;
  let end = start;
  while (end + 1 < future.length && future[end + 1].uvi > 0) end += 1;
  const peak = future
    .slice(start, end + 1)
    .reduce((best, h) => (h.uvi > best.uvi ? h : best));
  return {
    time: peak.time,
    uvi: peak.uvi,
    uvi_range: peak.uvi_range,
    level: peak.level,
    isTomorrow: peak.time.slice(0, 10) !== nowIso.slice(0, 10),
  };
}
