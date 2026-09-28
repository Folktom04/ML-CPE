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

export type SkyView =
  | { kind: 'sure'; nameTh: string; confidence: number; cloudFraction: number }
  | { kind: 'unsure'; top: RankedClass[]; confidence: number; cloudFraction: number };

/** What the result card shows: the class, or "ไม่แน่ใจ" + top 2 when confidence < 0.5. */
export function skyView(r: SkyImageResponse): SkyView {
  if (r.sky_confidence < LOW_CONFIDENCE) {
    return {
      kind: 'unsure',
      top: rankedClasses(r.sky_class_probs).slice(0, 2),
      confidence: r.sky_confidence,
      cloudFraction: r.cloud_fraction_rb,
    };
  }
  return {
    kind: 'sure',
    nameTh: r.sky_class_th,
    confidence: r.sky_confidence,
    cloudFraction: r.cloud_fraction_rb,
  };
}

/** 0.873 → "87%". */
export function pct(x: number): string {
  return `${Math.round(x * 100)}%`;
}
