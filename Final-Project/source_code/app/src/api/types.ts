/**
 * Response types of the UV Guard API. Keep in sync with source_code/api/schemas.py.
 * Times are the local start of the hourly interval in Asia/Bangkok, e.g. "2026-09-27T13:00:00+07:00".
 */

export type HourUV = {
  time: string;
  uvi: number;
  uvi_range: [number, number];
  uva_wm2: number;
  uvb_wm2: number;
  level: string;
  interval_adjusted: boolean;
  data_imputed: boolean;
};

export type PredictRequest = {
  lat: number;
  lon: number;
  skin_type: string;
};

export type PredictResponse = {
  uvi: number;
  uvi_range: [number, number];
  uva_wm2: number;
  uvb_wm2: number;
  level: string;
  skin_type: string;
  /** From alert_uvi (upper quantile); null when UV is too low for a burn time (night, dawn). */
  burn_minutes: number | null;
  cmf: number | null;
  advice: string[];
  forecast: HourUV[];
  next_safe_time: string | null;
  time: string;
  is_daylight: boolean;
  level_en: string;
  level_color: string;
  uvi_q90_cqr: number;
  /** max(q90 after CQR, uvi): drives alerts, burn time and advice. */
  alert_uvi: number;
  alert_level: string;
  interval_adjusted: boolean;
  data_imputed: boolean;
  note: string | null;
  disclaimer: string;
};

export type ForecastResponse = {
  lat: number;
  lon: number;
  hours: HourUV[];
  note: string | null;
  disclaimer: string;
};
