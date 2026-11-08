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

/**
 * What each sky class usually means for UV (general knowledge, WHO Global Solar UV Index guide
 * 2002: light or thin cloud has little effect and broken cloud can even raise UV for a while).
 * Shown as education only; the UVI on the home screen never changes with the photo.
 */
export const SKY_UV_MEANING_TH: Record<string, string> = {
  clear_sky: 'ฟ้าใสไม่มีเมฆช่วยบัง เป็นช่วงที่ UV แรงที่สุดของวัน',
  thin_white_clouds:
    'เมฆบางบัง UV ได้น้อย UV ยังผ่านลงมาได้เกือบทั้งหมด อย่าคิดว่าแดดไม่แรงเพราะไม่ร้อน',
  veil_clouds: 'เมฆบางคลุมฟ้าทำให้รู้สึกแดดอ่อน แต่ UV ยังผ่านลงมาได้มาก',
  patterned_clouds:
    'เมฆกระจายเป็นหย่อม UV เปลี่ยนเร็ว ช่วงที่แดดลอดช่องเมฆอาจแรงกว่าฟ้าใสได้ชั่วขณะ',
  thick_white_clouds: 'เมฆหนาช่วยลด UV ได้ แต่ถ้าแดดลอดช่องว่างของเมฆ UV ตรงนั้นยังแรง',
  thick_dark_clouds:
    'เมฆหนาสีเข้มลด UV ได้มาก แต่ UV ไม่เป็นศูนย์ และกลับมาแรงทันทีเมื่อเมฆเคลื่อนผ่าน',
};

export const SKY_UV_SOURCE_TH =
  'ความรู้ทั่วไปจาก WHO, Global Solar UV Index: A Practical Guide (2002)';

const LEVELS: CloudLevel[] = ['น้อย', 'ปานกลาง', 'มาก'];

export type CloudCheck = {
  photoLevel: CloudLevel;
  forecastLevel: CloudLevel;
  /** Open-Meteo cloud cover, 0-100 %. */
  forecastPct: number;
  verdict: 'match' | 'close' | 'differ';
  message: string;
};

/**
 * Compare the cloud seen in the photo (model fraction, else the red/blue proxy) with the
 * Open-Meteo cloud cover the UV model used for this hour. Same level → match, one level apart →
 * close, otherwise differ. Information only: the photo shows part of the sky and never changes
 * the UVI.
 */
export function compareCloud(
  view: SkyView,
  forecastPct: number | null | undefined,
): CloudCheck | null {
  if (typeof forecastPct !== 'number' || !Number.isFinite(forecastPct)) return null;
  const photo = view.cloudFractionCnn ?? view.cloudFraction;
  const photoLevel = cloudLevelTh(photo);
  const forecastLevel = cloudLevelTh(forecastPct / 100);
  const gap = Math.abs(LEVELS.indexOf(photoLevel) - LEVELS.indexOf(forecastLevel));
  const verdict = gap === 0 ? 'match' : gap === 1 ? 'close' : 'differ';
  const lessCloudInPhoto = LEVELS.indexOf(photoLevel) < LEVELS.indexOf(forecastLevel);
  let message: string;
  if (verdict === 'match') {
    message = 'ภาพตรงกับพยากรณ์ ค่า UV ที่แอปแสดงน่าจะใกล้เคียงสภาพตอนนี้';
  } else if (verdict === 'close') {
    message = 'ภาพใกล้เคียงกับพยากรณ์ อาจต่างกันเพราะภาพเห็นท้องฟ้าแค่บางส่วน';
  } else if (lessCloudInPhoto) {
    message = 'ในภาพเมฆน้อยกว่าพยากรณ์มาก UV จริงอาจแรงกว่าค่าที่แสดง ควรป้องกันตามค่าบนของช่วง UV';
  } else {
    message =
      'ในภาพเมฆมากกว่าพยากรณ์มาก แต่เมฆเคลื่อนเร็วและภาพเห็นแค่บางส่วน แอปจึงยังเตือนตามพยากรณ์';
  }
  return { photoLevel, forecastLevel, forecastPct, verdict, message };
}
