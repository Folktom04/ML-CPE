/**
 * Five-question skin-type quiz (day 19).
 *
 * A SHORT ADAPTATION of the Fitzpatrick skin-type questionnaire. It has NOT been validated
 * academically; the result is an estimate for education and warnings, not a diagnosis.
 *
 * The full questionnaire has 10 items scored 0-4 (total 0-40, types I-VI at 0-6, 7-13, 14-20,
 * 21-27, 28-34, 35-40). Eye and hair colour are dropped because almost every Thai user gives
 * the same answer; the five remaining items (unexposed skin colour, freckles, burning,
 * tanning degree, facial sensitivity) are scored 0-4, total 0-20. The type cut-offs are the
 * full scale's halved: 3.5, 7, 10.5, 14, 17.5. A score that lands exactly on a cut-off
 * (7 or 14) goes to the LIGHTER type, which burns sooner, so warnings err on the safe side:
 *
 *   I 0-3 · II 4-7 · III 8-10 · IV 11-14 · V 15-17 · VI 18-20
 */

export const SKIN_TYPES = ['I', 'II', 'III', 'IV', 'V', 'VI'] as const;
export type SkinType = (typeof SKIN_TYPES)[number];

/** MED (J/m²) by skin type: same values as src/risk.py. */
export const MED_J_M2: Record<SkinType, number> = {
  I: 200,
  II: 250,
  III: 350,
  IV: 450,
  V: 600,
  VI: 1000,
};

export const SKIN_DESCRIPTION_TH: Record<SkinType, string> = {
  I: 'ผิวขาวซีดมาก ไหม้ง่ายมาก แทบไม่คล้ำ',
  II: 'ผิวขาว ไหม้ง่าย คล้ำขึ้นเล็กน้อย',
  III: 'ผิวขาวเหลืองถึงสองสี ไหม้บ้าง คล้ำขึ้นพอสมควร',
  IV: 'ผิวสีน้ำผึ้งหรือแทน ไหม้น้อย คล้ำง่าย',
  V: 'ผิวน้ำตาลเข้ม ไหม้ยาก คล้ำง่ายมาก',
  VI: 'ผิวน้ำตาลเข้มมากถึงดำ แทบไม่ไหม้',
};

export const QUIZ_NOTE_TH =
  'แบบสอบถามนี้เป็นแบบย่อดัดแปลงจาก Fitzpatrick ยังไม่ผ่านการตรวจสอบทางวิชาการ ' +
  'ผลเป็นการประมาณเพื่อการศึกษาและการเตือนเท่านั้น ไม่ใช่การวินิจฉัยทางการแพทย์';

export type QuizQuestion = { id: string; text: string; options: string[] };

/** Five questions; option index = score (0 = burns most easily ... 4 = least). */
export const QUESTIONS: QuizQuestion[] = [
  {
    id: 'colour',
    text: 'ผิวบริเวณที่ไม่ค่อยโดนแดด (เช่น ท้องแขนด้านใน) เป็นสีอะไร',
    options: [
      'ขาวซีด อมชมพู',
      'ขาว',
      'ขาวอมเหลือง หรือสองสีอ่อน',
      'สีน้ำผึ้ง หรือแทน',
      'น้ำตาลเข้มถึงดำ',
    ],
  },
  {
    id: 'freckles',
    text: 'มีกระ (จุดสีน้ำตาลเล็ก ๆ) บนผิวที่ไม่ค่อยโดนแดดมากแค่ไหน',
    options: ['มาก', 'พอสมควร', 'เล็กน้อย', 'แทบไม่มี', 'ไม่มีเลย'],
  },
  {
    id: 'burn',
    text: 'ถ้าอยู่กลางแดดจัด 1 ชั่วโมงโดยไม่ทาครีมกันแดด ผิวเป็นอย่างไร',
    options: [
      'แดงไหม้ แสบ พองหรือลอก',
      'แดงไหม้ แล้วลอก',
      'ไหม้บ้าง บางครั้งลอก',
      'ไหม้น้อยมาก',
      'ไม่เคยไหม้',
    ],
  },
  {
    id: 'tan',
    text: 'หลังโดนแดดติดกันหลายวัน ผิวคล้ำขึ้นแค่ไหน',
    options: [
      'ไม่คล้ำเลย มีแต่แดง',
      'คล้ำขึ้นเล็กน้อย',
      'คล้ำขึ้นพอสมควร',
      'คล้ำขึ้นมาก',
      'ผิวเข้มอยู่แล้ว และคล้ำขึ้นเร็วมาก',
    ],
  },
  {
    id: 'face',
    text: 'ผิวหน้าของคุณไวต่อแดดแค่ไหน',
    options: ['ไวมาก', 'ไว', 'ปานกลาง', 'ไม่ค่อยไว', 'ไม่ไวเลย'],
  },
];

/** Highest score of each type, in order (a boundary score belongs to the lighter type). */
const UPPER_SCORE: [number, SkinType][] = [
  [3, 'I'],
  [7, 'II'],
  [10, 'III'],
  [14, 'IV'],
  [17, 'V'],
  [20, 'VI'],
];

export const MAX_SCORE = 20;

/** Skin type of a total score 0-20 (integer). Throws on anything else. */
export function scoreToSkinType(score: number): SkinType {
  if (!Number.isInteger(score) || score < 0 || score > MAX_SCORE) {
    throw new RangeError(`score must be an integer 0-${MAX_SCORE}, got ${score}`);
  }
  return UPPER_SCORE.find(([upper]) => score <= upper)![1];
}

/**
 * Total score of the answers (option indexes, one per question). Throws if a question is
 * unanswered or an index is out of range.
 */
export function totalScore(answers: (number | null)[]): number {
  if (answers.length !== QUESTIONS.length) {
    throw new RangeError(`expected ${QUESTIONS.length} answers, got ${answers.length}`);
  }
  return answers.reduce<number>((sum, a, i) => {
    if (a === null || !Number.isInteger(a) || a < 0 || a >= QUESTIONS[i].options.length) {
      throw new RangeError(`question ${i + 1} is not answered`);
    }
    return sum + a;
  }, 0);
}

/** Minutes to burn at a given UVI (same formula as the API: MED / (UVI × 0.025 × 60)). */
export function burnMinutesAt(skin: SkinType, uvi: number): number {
  return Math.floor(MED_J_M2[skin] / (uvi * 0.025 * 60));
}

export function isSkinType(v: unknown): v is SkinType {
  return typeof v === 'string' && (SKIN_TYPES as readonly string[]).includes(v);
}
