import {
  alertIsHigher,
  formatBurn,
  formatClock,
  formatHourInterval,
  formatRange,
  levelColor,
  levelIndex,
  textOn,
  WHO_COLORS,
  WHO_LEVELS,
} from '@/lib/uv';

describe('levelIndex (same rule as src/metrics.py who_level)', () => {
  it.each([
    [-1, 0],
    [0, 0],
    [2.49, 0],
    [2.5, 1], // x.5 rounds up
    [5.49, 1],
    [5.5, 2],
    [7.4, 2],
    [7.5, 3],
    [10.49, 3],
    [10.5, 4],
    [14, 4],
    [Number.NaN, 0],
  ])('UVI %p -> level %p', (uvi, idx) => {
    expect(levelIndex(uvi)).toBe(idx);
  });
});

describe('colours', () => {
  it('uses the WHO palette from the project rules', () => {
    expect(WHO_COLORS).toEqual(['#3E9B4F', '#D9A400', '#E36B12', '#D22F3A', '#8A3FC2']);
    expect(WHO_LEVELS).toEqual(['ต่ำ', 'ปานกลาง', 'สูง', 'สูงมาก', 'รุนแรงมาก']);
  });

  it('maps a level name to its colour and falls back to UVI for unknown names', () => {
    expect(levelColor('สูงมาก', 0)).toBe('#D22F3A');
    expect(levelColor('???', 11.2)).toBe('#8A3FC2');
  });

  it('uses dark text on yellow only', () => {
    expect(textOn('#D9A400')).toBe('#1F1F1F');
    expect(textOn('#3E9B4F')).toBe('#FFFFFF');
  });

  it('flags an alert level above the shown level', () => {
    expect(alertIsHigher('ปานกลาง', 'สูง')).toBe(true);
    expect(alertIsHigher('สูง', 'สูง')).toBe(false);
  });
});

describe('formatBurn', () => {
  it.each([
    [35, true, '35 นาที'],
    [59.9, true, '59 นาที'],
    [60, true, '1 ชม.'],
    [95, true, '1 ชม. 35 นาที'],
    [120, true, 'มากกว่า 2 ชม.'],
    [null, true, 'UV ต่ำมาก ยังไม่เสี่ยงผิวไหม้'],
    [null, false, 'ไม่มีความเสี่ยง (กลางคืน)'],
  ])('%p min (daylight %p) -> %p', (min, day, text) => {
    expect(formatBurn(min as number | null, day as boolean)).toBe(text);
  });
});

describe('time formatting keeps the API local time (Asia/Bangkok)', () => {
  it('formats clock and hourly interval without re-zoning', () => {
    expect(formatClock('2026-09-27T16:00:00+07:00')).toBe('16:00');
    expect(formatHourInterval('2026-09-27T13:00:00+07:00')).toBe('13:00–14:00');
    expect(formatHourInterval('2026-09-27T23:00:00+07:00')).toBe('23:00–00:00');
  });

  it('formats a range with one decimal', () => {
    expect(formatRange([4.94, 6.66])).toBe('4.9–6.7');
  });
});
