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
  /** max(q90 after CQR, uvi): drives alerts and the burn dose (day 22). */
  alert_uvi: number;
  /** Clear-sky UVI >= 0.5; no alerts at night. */
  is_daylight: boolean;
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

/** Settings the server stores for remote alerts (PUT sends only the fields given). */
export type UserSettingsBody = {
  skin_type?: string | null;
  notify_enabled?: boolean;
  alert_threshold?: number;
  alert_burn_minutes?: number;
  /** Thai province name only (never GPS coordinates); sent only with consent. */
  province?: string | null;
};

/** Response of POST /users and PUT /users/{id}/settings (never contains the device id). */
export type UserResponse = {
  id: number;
  skin_type: string;
  province: string | null;
  notify_enabled: boolean;
  alert_threshold: number;
  /** alert_threshold − 2, set by the server. */
  safe_threshold: number;
  alert_burn_minutes: number;
  updated_at: string;
  disclaimer: string;
};

/** Response of POST /sky-image: supporting information only, never changes the UVI. */
export type SkyImageResponse = {
  /** SWIMCAT-ext class id, e.g. "thick_white_clouds". */
  sky_class: string;
  sky_class_th: string;
  /** Softmax probability of sky_class (0-1). */
  sky_confidence: number;
  sky_class_probs: Record<string, number>;
  /** Red/blue-ratio cloud fraction proxy (0-1), not a model output. */
  cloud_fraction_rb: number;
  /**
   * Cloud fraction IN THE IMAGE (0-1) from the SWIMSEG head, not the whole sky. Present only
   * while that head's one-time test passed its criteria (C1/C2).
   */
  cloud_fraction_cnn?: number;
  reliability: Record<string, string>;
  note: string;
  stored: boolean;
  disclaimer: string;
};
