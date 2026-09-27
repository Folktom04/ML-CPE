import type { HourUV, PredictResponse } from '@/api/types';
import { levelIndex, WHO_LEVELS } from '@/lib/uv';

/** Shaped like the day-16 smoke test (Pathum Thani, 27 Sep 2026 ~13:00, skin type III). */
export function samplePredict(overrides: Partial<PredictResponse> = {}): PredictResponse {
  return {
    uvi: 5.49,
    uvi_range: [4.94, 6.66],
    uva_wm2: 28.4,
    uvb_wm2: 0.83,
    level: 'ปานกลาง',
    skin_type: 'III',
    burn_minutes: 35,
    cmf: 0.497,
    advice: ['ทาครีมกันแดด SPF 30+ PA+++', 'สวมหมวกและแว่นกันแดด'],
    forecast: [],
    next_safe_time: '2026-09-27T16:00:00+07:00',
    time: '2026-09-27T13:00:00+07:00',
    is_daylight: true,
    level_en: 'Moderate',
    level_color: '#D9A400',
    uvi_q90_cqr: 6.66,
    alert_uvi: 6.66,
    alert_level: 'สูง',
    interval_adjusted: false,
    data_imputed: false,
    note: null,
    disclaimer: 'ค่านี้เป็นการประมาณเพื่อการศึกษาและการเตือนเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์',
    ...overrides,
  };
}

/** What /predict really returns at night (UVI 0): the API still sends the level-ต่ำ advice. */
export function sampleNight(overrides: Partial<PredictResponse> = {}): PredictResponse {
  return samplePredict({
    uvi: 0,
    uvi_range: [0, 0],
    uva_wm2: 0,
    uvb_wm2: 0,
    level: 'ต่ำ',
    alert_uvi: 0,
    alert_level: 'ต่ำ',
    burn_minutes: null,
    is_daylight: false,
    time: '2026-09-27T20:00:00+07:00',
    advice: ['ออกกลางแจ้งได้ตามปกติ', 'ถ้าอยู่กลางแจ้งนานหรืออยู่ใกล้น้ำ/ทราย ควรใส่แว่นกันแดด'],
    ...overrides,
  });
}

/** Hourly forecast starting at `startIso` (Bangkok local, +07:00), one UVI per hour. */
export function sampleHours(startIso: string, uvis: number[]): HourUV[] {
  const start = Date.parse(`${startIso.slice(0, 19)}Z`); // step the local wall time as if UTC
  return uvis.map((uvi, i) => ({
    time: `${new Date(start + i * 3600e3).toISOString().slice(0, 19)}+07:00`,
    uvi,
    uvi_range: [Math.max(0, uvi - 0.5), uvi + 0.8] as [number, number],
    uva_wm2: uvi * 5,
    uvb_wm2: uvi * 0.15,
    level: WHO_LEVELS[levelIndex(uvi)],
    interval_adjusted: false,
    data_imputed: false,
  }));
}
