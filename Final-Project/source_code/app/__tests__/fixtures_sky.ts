import type { SkyImageResponse } from '@/api/types';

/** A /sky-image response; `confidence` sets both sky_confidence and the chosen class's prob. */
export function sampleSky(confidence = 0.87): SkyImageResponse {
  const rest = (1 - confidence) / 5;
  return {
    sky_class: 'thick_white_clouds',
    sky_class_th: 'เมฆหนาสีขาว',
    sky_confidence: confidence,
    sky_class_probs: {
      clear_sky: rest,
      patterned_clouds: rest,
      thick_dark_clouds: rest,
      thick_white_clouds: confidence,
      thin_white_clouds: rest,
      veil_clouds: rest,
    },
    cloud_fraction_rb: 0.62,
    reliability: {
      sky_class: 'ผ่านเกณฑ์ (ความแม่นบนชุดทดสอบ 97%) แต่ยังไม่ได้ทดสอบกับภาพจากมือถือ',
      cloud_fraction_rb:
        'ประมาณจากอัตราส่วนสีแดง/น้ำเงิน (ไม่ใช่โมเดล) ยังไม่ได้ทดสอบกับภาพจากมือถือ',
    },
    note: 'ผลจากภาพท้องฟ้าเป็นข้อมูลประกอบเท่านั้น ไม่ได้ใช้คำนวณค่า UV',
    stored: false,
    disclaimer: 'ค่านี้เป็นการประมาณเพื่อการศึกษาและการเตือนเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์',
  };
}

/** Low-confidence answer: veil 0.41, thin white 0.33, the rest share the remainder. */
export function unsureSky(): SkyImageResponse {
  return {
    ...sampleSky(0.41),
    sky_class: 'veil_clouds',
    sky_class_th: 'เมฆบางคลุมทั่วฟ้า',
    sky_class_probs: {
      clear_sky: 0.05,
      patterned_clouds: 0.1,
      thick_dark_clouds: 0.03,
      thick_white_clouds: 0.08,
      thin_white_clouds: 0.33,
      veil_clouds: 0.41,
    },
  };
}
