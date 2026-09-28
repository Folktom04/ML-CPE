/**
 * Sky photo helpers (day 20). The photo is re-encoded before upload so that no EXIF (GPS, time,
 * phone model) leaves the phone, and every temporary file is deleted afterwards.
 */

import type { SkyImageResponse } from '@/api/types';

/** Longest side of the uploaded JPEG (px); the model works on a much smaller centre crop. */
export const UPLOAD_MAX_SIDE = 1024;
export const UPLOAD_JPEG_QUALITY = 0.8;

/** Below this softmax probability the app says "ไม่แน่ใจ" and shows the top 2 classes. */
export const LOW_CONFIDENCE = 0.5;

export const SKY_NOTICE_TH = 'ภาพจะถูกส่งไปวิเคราะห์ที่เซิร์ฟเวอร์แล้วลบทันที ไม่มีการเก็บภาพ';

export const SKY_SUPPORTING_TH = 'ข้อมูลประกอบเท่านั้น ไม่เปลี่ยนค่า UVI';

export const SKY_DOMAIN_GAP_TH =
  'โมเดลทดสอบกับภาพจากเว็บ ความแม่นยำกับภาพจากกล้องมือถือยังไม่ได้วัด';

/**
 * Thai names of the SWIMCAT-ext classes for the top-2 list. Must equal SWIM_CLASS_TH in
 * source_code/src/sky_infer.py (checked by tests/test_app_sky_names.py).
 */
export const SKY_CLASS_TH: Record<string, string> = {
  clear_sky: 'ท้องฟ้าแจ่มใส',
  patterned_clouds: 'เมฆเป็นลวดลาย',
  thick_dark_clouds: 'เมฆหนาสีเข้ม',
  thick_white_clouds: 'เมฆหนาสีขาว',
  thin_white_clouds: 'เมฆบางสีขาว',
  veil_clouds: 'เมฆบางคลุมทั่วฟ้า',
};

export type RankedClass = { name: string; nameTh: string; prob: number };

/** Classes sorted by probability, highest first. */
export function rankedClasses(probs: Record<string, number>): RankedClass[] {
  return Object.entries(probs)
    .filter(([, p]) => Number.isFinite(p))
    .sort((a, b) => b[1] - a[1])
    .map(([name, prob]) => ({ name, nameTh: SKY_CLASS_TH[name] ?? name, prob }));
}

type CloudParts = {
  /** Red/blue colour proxy (0-1). */
  cloudFraction: number;
  /** SWIMSEG head (0-1), null when the API does not send it. */
  cloudFractionCnn: number | null;
};

export type SkyView =
  | ({ kind: 'sure'; nameTh: string; confidence: number } & CloudParts)
  | ({ kind: 'unsure'; top: RankedClass[]; confidence: number } & CloudParts);

/** Thai labels of the `reliability` keys. */
export const RELIABILITY_LABEL_TH: Record<string, string> = {
  sky_class: 'สภาพท้องฟ้า',
  cloud_fraction_rb: 'สัดส่วนเมฆ (สี)',
  cloud_fraction_cnn: 'สัดส่วนเมฆ (โมเดล)',
};

export const CLOUD_IN_IMAGE_TH = 'สัดส่วนเมฆในภาพ ไม่ใช่ทั้งท้องฟ้า';

/**
 * The SWIMSEG head shrinks towards mid values (test: it rarely predicts below ~15 %), so a clear
 * photo may read as "น้อย" rather than 0 %; the app shows a level, not a percentage.
 */
export const CLOUD_CLEAR_NOTE_TH = 'ภาพท้องฟ้าใสอาจแสดงเป็นเมฆน้อย';

/** Upper bounds of the levels: น้อย < 0.30 ≤ ปานกลาง ≤ 0.70 < มาก. */
export const CLOUD_LEVEL_LOW_MAX = 0.3;
export const CLOUD_LEVEL_MID_MAX = 0.7;

export type CloudLevel = 'น้อย' | 'ปานกลาง' | 'มาก';

/** Level of the model's cloud fraction: < 30 % น้อย, 30–70 % ปานกลาง, > 70 % มาก. */
export function cloudLevelTh(fraction: number): CloudLevel {
  if (fraction < CLOUD_LEVEL_LOW_MAX) return 'น้อย';
  if (fraction <= CLOUD_LEVEL_MID_MAX) return 'ปานกลาง';
  return 'มาก';
}

/** What the result card shows: the class, or "ไม่แน่ใจ" + top 2 when confidence < 0.5. */
export function skyView(r: SkyImageResponse): SkyView {
  const cloud: CloudParts = {
    cloudFraction: r.cloud_fraction_rb,
    cloudFractionCnn: typeof r.cloud_fraction_cnn === 'number' ? r.cloud_fraction_cnn : null,
  };
  if (r.sky_confidence < LOW_CONFIDENCE) {
    return {
      kind: 'unsure',
      top: rankedClasses(r.sky_class_probs).slice(0, 2),
      confidence: r.sky_confidence,
      ...cloud,
    };
  }
  return {
    kind: 'sure',
    nameTh: r.sky_class_th,
    confidence: r.sky_confidence,
    ...cloud,
  };
}

/** 0.873 → "87%". */
export function pct(x: number): string {
  return `${Math.round(x * 100)}%`;
}
