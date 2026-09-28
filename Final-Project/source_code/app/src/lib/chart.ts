/**
 * Pure helpers for the hourly UV chart (day 19): which hours to plot, the y-scale and labels.
 */

import type { HourUV, PredictResponse } from '@/api/types';

/** WHO level boundaries drawn as hairline gridlines (UVI). */
export const LEVEL_GRIDLINES = [3, 6, 8, 11] as const;

/** Smallest y-axis top, so a low-UV day is not stretched to look alarming. */
export const MIN_Y_MAX = 12;

/** The current hour (from /predict) followed by the forecast hours, in time order. */
export function chartHours(data: PredictResponse): HourUV[] {
  const now: HourUV = {
    time: data.time,
    uvi: data.uvi,
    uvi_range: data.uvi_range,
    uva_wm2: data.uva_wm2,
    uvb_wm2: data.uvb_wm2,
    level: data.level,
    interval_adjusted: data.interval_adjusted,
    data_imputed: data.data_imputed,
  };
  return [now, ...data.forecast.filter((h) => h.time > data.time)];
}

/**
 * Top of the y-axis: at least MIN_Y_MAX, else the highest upper bound (q90) rounded up to an
 * even number, so the whisker of every hour fits.
 */
export function yMax(hours: HourUV[]): number {
  const top = Math.max(0, ...hours.map((h) => Math.max(h.uvi, h.uvi_range[1])));
  return Math.max(MIN_Y_MAX, Math.ceil(top / 2) * 2);
}

/** Pixel height of a UVI value on a plot of `height` px (clipped to 0..height). */
export function scaleY(uvi: number, max: number, height: number): number {
  if (!Number.isFinite(uvi) || max <= 0) return 0;
  return Math.min(height, Math.max(0, (uvi / max) * height));
}

/** Index of the hour with the highest UVI (first one on ties), or -1 if there are no hours. */
export function peakIndex(hours: HourUV[]): number {
  let best = -1;
  hours.forEach((h, i) => {
    if (best < 0 || h.uvi > hours[best].uvi) best = i;
  });
  return best;
}

/** Hour label "HH" for the x-axis: every `step` hours, and always for the first column. */
export function hourTick(iso: string, index: number, step = 3): string | null {
  const m = /T(\d{2}):/.exec(iso);
  if (!m) return null;
  return index === 0 || Number(m[1]) % step === 0 ? m[1] : null;
}

/**
 * Column the chart opens on: the current hour in daytime; at night the peak of the next
 * daytime run (first run of hours with UVI > 0), so the chart does not open on dark hours.
 */
export function initialFocusIndex(hours: HourUV[], isDaylight: boolean): number {
  if (isDaylight || hours.length === 0) return 0;
  const start = hours.findIndex((h, i) => i > 0 && h.uvi > 0);
  if (start < 0) return 0;
  let best = start;
  for (let i = start + 1; i < hours.length && hours[i].uvi > 0; i += 1) {
    if (hours[i].uvi > hours[best].uvi) best = i;
  }
  return best;
}

/** Horizontal scroll offset that centres column `index` (clamped to the content). */
export function scrollOffsetFor(
  index: number,
  slotWidth: number,
  viewWidth: number,
  count: number,
): number {
  const content = slotWidth * count;
  const centre = index * slotWidth + slotWidth / 2 - viewWidth / 2;
  return Math.max(0, Math.min(centre, Math.max(0, content - viewWidth)));
}
