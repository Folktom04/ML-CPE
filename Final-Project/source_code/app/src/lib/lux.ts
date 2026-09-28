/**
 * Phone ambient-light readings (day 20, Android only). The values are NOT calibrated: the
 * sun / shade exposure factor is fitted from field data on day 25, and lux never changes the UVI.
 */

/** Keep this many seconds of readings for the displayed value. */
export const LUX_WINDOW_S = 2;

export type LuxSample = { lux: number; t: number };

/** Add a sample and drop the ones older than the window (t in seconds). Invalid values are skipped. */
export function pushLux(samples: LuxSample[], s: LuxSample, windowS = LUX_WINDOW_S): LuxSample[] {
  const keep = samples.filter((x) => s.t - x.t <= windowS);
  if (Number.isFinite(s.lux) && s.lux >= 0) keep.push(s);
  return keep;
}

/** Median lux of the samples (null when there is none); robust to single spikes. */
export function medianLux(samples: LuxSample[]): number | null {
  const v = samples
    .map((s) => s.lux)
    .filter((x) => Number.isFinite(x) && x >= 0)
    .sort((a, b) => a - b);
  if (v.length === 0) return null;
  const m = Math.floor(v.length / 2);
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}

/** "12,345 lux" with a thousands separator (whole lux). */
export function formatLux(lux: number): string {
  return `${Math.round(lux).toLocaleString('en-US')} lux`;
}
