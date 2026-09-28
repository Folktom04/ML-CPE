/**
 * Erythemal UV dose while "in the sun" (day 22), from the hourly forecast.
 *
 * Dose rate = alert_uvi × 0.025 W/m² (1 UVI = 0.025 W/m²), so the dose over t seconds is
 * alert_uvi × 0.025 × t J/m². The UPPER value (alert_uvi = max(q90, point)) is used, as for every
 * warning, and full sun is assumed: time in the shade, clothing and sunscreen are not modelled,
 * so the real time to 80 % of the MED is longer than computed (warnings come early, not late).
 */

import type { HourUV } from '@/api/types';
import { MED_J_M2, type SkinType } from '@/lib/skinQuiz';

export const WM2_PER_UVI = 0.025;
export const BURN_FRACTION = 0.8;
const HOUR_MS = 3600 * 1000;

/** Start of an hourly interval in ms (API times are local ISO strings with an offset). */
export function hourStartMs(h: HourUV): number {
  return Date.parse(h.time);
}

/**
 * Dose (J/m²) from `fromMs` to `toMs`, hour by hour. Returns null if a part of the span is not
 * covered by `hours` (the forecast ends), because the dose there is unknown.
 */
export function doseBetween(hours: HourUV[], fromMs: number, toMs: number): number | null {
  if (toMs <= fromMs) return 0;
  let dose = 0;
  let covered = fromMs;
  for (const h of hours) {
    const start = hourStartMs(h);
    const end = start + HOUR_MS;
    const a = Math.max(start, fromMs);
    const b = Math.min(end, toMs);
    if (b <= a) continue;
    if (a > covered) return null; // a gap in the forecast
    dose += Math.max(0, h.alert_uvi) * WM2_PER_UVI * ((b - a) / 1000);
    covered = b;
  }
  return covered >= toMs ? dose : null;
}

/**
 * Time (ms) at which the dose since `fromMs` reaches `targetJm2`, or null if it is not reached
 * within the forecast.
 */
export function timeToDose(hours: HourUV[], fromMs: number, targetJm2: number): number | null {
  let dose = 0;
  let covered = fromMs;
  for (const h of hours) {
    const start = hourStartMs(h);
    const end = start + HOUR_MS;
    if (end <= fromMs) continue;
    const a = Math.max(start, fromMs);
    if (a > covered) return null; // a gap in the forecast
    const rate = Math.max(0, h.alert_uvi) * WM2_PER_UVI; // J/m² per second
    const need = targetJm2 - dose;
    const span = (end - a) / 1000;
    if (rate > 0 && rate * span >= need) return a + (need / rate) * 1000;
    dose += rate * span;
    covered = end;
  }
  return null;
}

export type SunStatus = {
  /** Fraction of the MED received so far (0-1+), or null if the forecast does not cover it. */
  fractionNow: number | null;
  /** When BURN_FRACTION of the MED is reached (ms), or null if not within the forecast. */
  warnAt: number | null;
};

/** Dose status of a "going out" session that started at `startMs`, at time `nowMs`. */
export function sunStatus(
  hours: HourUV[],
  skin: SkinType,
  startMs: number,
  nowMs: number,
): SunStatus {
  const med = MED_J_M2[skin];
  const got = doseBetween(hours, startMs, nowMs);
  return {
    fractionNow: got === null ? null : got / med,
    warnAt: timeToDose(hours, startMs, BURN_FRACTION * med),
  };
}
