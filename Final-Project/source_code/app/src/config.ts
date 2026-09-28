/**
 * App configuration (day 18).
 *
 * The API address comes from EXPO_PUBLIC_API_URL (see .env.example). On a real phone with
 * Expo Go, `localhost` is the phone itself, so use the computer's LAN IP instead.
 */

export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(
  /\/+$/,
  '',
);

/** Request timeout for /predict (ms). The API may call Open-Meteo on a cache miss. */
export const REQUEST_TIMEOUT_MS = 20000;

/**
 * Default location until GPS / province selection is added (day 21):
 * Pathum Thani, the location the model was trained on.
 */
export const DEFAULT_LOCATION = { lat: 14.02, lon: 100.52, name: 'ปทุมธานี' } as const;

/** Skin type used until the user does the quiz or picks a type (settings.skinType is null). */
export const DEFAULT_SKIN_TYPE = 'III';

/** Shown when the API is unreachable, so the disclaimer is never missing. */
export const DISCLAIMER_TH =
  'ค่านี้เป็นการประมาณเพื่อการศึกษาและการเตือนเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์';
