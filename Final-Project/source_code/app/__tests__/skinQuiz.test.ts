import {
  burnMinutesAt,
  MAX_SCORE,
  QUESTIONS,
  QUIZ_NOTE_TH,
  scoreToSkinType,
  SKIN_TYPES,
  totalScore,
} from '@/lib/skinQuiz';

it('has 5 questions with 5 options each (scores 0-4, total 0-20)', () => {
  expect(QUESTIONS).toHaveLength(5);
  QUESTIONS.forEach((q) => expect(q.options).toHaveLength(5));
  expect(MAX_SCORE).toBe(20);
});

// Every edge of every range: the first and last score of each type.
it.each([
  [0, 'I'],
  [3, 'I'],
  [4, 'II'],
  [7, 'II'], // exactly on the halved cut-off 7 -> lighter type
  [8, 'III'],
  [10, 'III'],
  [11, 'IV'],
  [14, 'IV'], // exactly on the halved cut-off 14 -> lighter type
  [15, 'V'],
  [17, 'V'],
  [18, 'VI'],
  [20, 'VI'],
])('score %p -> type %p', (score, type) => {
  expect(scoreToSkinType(score)).toBe(type);
});

/** Type index on the full 10-item Fitzpatrick scale (0-40). */
function fullScaleIndex(total: number): number {
  return [6, 13, 20, 27, 34, 40].findIndex((upper) => total <= upper);
}

it('never gives a darker type than the full scale at twice the score (safe side)', () => {
  for (let s = 0; s <= MAX_SCORE; s += 1) {
    const idx = SKIN_TYPES.indexOf(scoreToSkinType(s));
    const full = fullScaleIndex(2 * s);
    expect(idx).toBeLessThanOrEqual(full);
    // it differs only on the two exact cut-offs (7 -> 14, 14 -> 28), by one lighter type
    if (s === 7 || s === 14) expect(idx).toBe(full - 1);
    else expect(idx).toBe(full);
  }
});

it('types are non-decreasing in the score and all six are reachable', () => {
  const types = Array.from({ length: MAX_SCORE + 1 }, (_, s) => scoreToSkinType(s));
  const idx = types.map((t) => SKIN_TYPES.indexOf(t));
  idx.slice(1).forEach((v, i) => expect(v).toBeGreaterThanOrEqual(idx[i]));
  expect(new Set(types)).toEqual(new Set(SKIN_TYPES));
});

it.each([-1, 21, 3.5, NaN])('rejects score %p', (score) => {
  expect(() => scoreToSkinType(score)).toThrow(RangeError);
});

it('totals answers and refuses unanswered or out-of-range answers', () => {
  expect(totalScore([0, 1, 2, 3, 4])).toBe(10);
  expect(() => totalScore([0, 1, null, 3, 4])).toThrow(/question 3/);
  expect(() => totalScore([0, 1, 2, 3, 5])).toThrow(RangeError);
  expect(() => totalScore([0, 1, 2])).toThrow(RangeError);
});

it('burn minutes use the API formula MED / (UVI x 0.025 x 60), truncated', () => {
  expect(burnMinutesAt('III', 10)).toBe(23); // 350 / 15 = 23.3
  expect(burnMinutesAt('I', 10)).toBe(13);
  expect(burnMinutesAt('VI', 10)).toBe(66);
});

it('states that the quiz is an unvalidated adaptation', () => {
  expect(QUIZ_NOTE_TH).toContain('แบบย่อดัดแปลงจาก Fitzpatrick');
  expect(QUIZ_NOTE_TH).toContain('ยังไม่ผ่านการตรวจสอบทางวิชาการ');
});
