import type { PredictResponse } from '@/api/types';

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
