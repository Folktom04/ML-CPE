import {
  alertIsHigher,
  formatBurn,
  formatClock,
  formatHourInterval,
  formatRange,
  levelColor,
  levelIndex,
  nextDaytimePeak,
  textOn,
  WHO_COLORS,
  WHO_LEVELS,
} from '@/lib/uv';

import { sampleHours } from './fixtures';

describe('nextDaytimePeak', () => {
  const NIGHT = '2026-09-27T20:00:00+07:00';
  // 20:00 tonight: 10 dark hours, then 06:00-18:00 tomorrow with a noon peak, then dark
  const tomorrow = [0.1, 0.8, 2.1, 4.0, 6.2, 8.4, 9.6, 9.1, 7.3, 5.0, 2.6, 0.9, 0.2];
  const hours = sampleHours(NIGHT, [...Array(10).fill(0), ...tomorrow, 0, 0]);

  it('returns the highest hour of the next daytime period, marked as tomorrow', () => {
    const p = nextDaytimePeak(hours, NIGHT)!;
    expect(p.uvi).toBe(9.6);
    expect(p.time).toBe('2026-09-28T12:00:00+07:00');
    expect(p.level).toBe('สูงมาก');
    expect(p.uvi_range).toEqual([9.1, 10.4]);
    expect(p.isTomorrow).toBe(true);
  });

  it('after midnight the coming daytime is "today"', () => {
    const p = nextDaytimePeak(hours.slice(6), '2026-09-28T02:00:00+07:00')!;
    expect(p.uvi).toBe(9.6);
    expect(p.isTomorrow).toBe(false);
  });

  it('ignores the current hour and stops at the end of the first daytime run', () => {
    const two = sampleHours(NIGHT, [0, 3, 0, 12]);
    expect(nextDaytimePeak(two, NIGHT)!.uvi).toBe(3);
    expect(nextDaytimePeak(two, '2026-09-27T21:00:00+07:00')!.uvi).toBe(12);
  });

  it('returns null when the forecast has no daytime', () => {
    expect(nextDaytimePeak(sampleHours(NIGHT, [0, 0, 0]), NIGHT)).toBeNull();
    expect(nextDaytimePeak([], NIGHT)).toBeNull();
  });
});

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
