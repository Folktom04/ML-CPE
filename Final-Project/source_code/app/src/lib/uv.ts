/**
 * WHO UV levels, colours and display formatting.
 * Levels mirror src/metrics.py (who_level): round UVI to an integer (x.5 up), then
 * 0-2 ต่ำ, 3-5 ปานกลาง, 6-7 สูง, 8-10 สูงมาก, 11+ รุนแรงมาก.
 */

export const WHO_LEVELS = ['ต่ำ', 'ปานกลาง', 'สูง', 'สูงมาก', 'รุนแรงมาก'] as const;
export const WHO_COLORS = ['#3E9B4F', '#D9A400', '#E36B12', '#D22F3A', '#8A3FC2'] as const;
const WHO_LOWER_BOUNDS = [0, 3, 6, 8, 11];

/** WHO level index 0-4 of a UVI value (same rounding as the API). */
export function levelIndex(uvi: number): number {
  if (!Number.isFinite(uvi)) return 0;
  const rounded = Math.floor(Math.max(uvi, 0) + 0.5);
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
