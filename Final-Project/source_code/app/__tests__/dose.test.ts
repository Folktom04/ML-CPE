import { BURN_FRACTION, doseBetween, sunStatus, timeToDose, WM2_PER_UVI } from '@/lib/dose';
import { burnMinutesAt, MED_J_M2 } from '@/lib/skinQuiz';

import { mkHours } from './fixtures';

const at = (iso: string) => Date.parse(iso);
const START = '2026-09-29T10:00:00+07:00';

it('constant UV: 80 % of the MED at 80 % of the burn time of the API formula', () => {
  const hours = mkHours(START, [10, 10, 10, 10]);
  const from = at('2026-09-29T10:20:00+07:00');
  const t = timeToDose(hours, from, BURN_FRACTION * MED_J_M2.III)!;
  const minutes = (t - from) / 60000;
  // MED / (UVI x 0.025 x 60) = 350 / 15 = 23.3 min to 100 %
  expect(minutes).toBeCloseTo(0.8 * (350 / 15), 6);
  expect(Math.floor(minutes / 0.8)).toBe(burnMinutesAt('III', 10));
});

it('dose crosses hours with different UV (uses alert_uvi, the upper value)', () => {
  const hours = mkHours(START, [4, 8, 12]);
  const from = at('2026-09-29T10:30:00+07:00');
  const to = at('2026-09-29T12:15:00+07:00');
  const expected = (4 * 1800 + 8 * 3600 + 12 * 900) * WM2_PER_UVI;
  expect(doseBetween(hours, from, to)).toBeCloseTo(expected, 6);
  // reaches 280 J/m2 during the 11:00 hour: 4*0.025*1800 = 180, +8*0.025*t = 100 -> t = 500 s
  expect(timeToDose(hours, from, 280)).toBe(at('2026-09-29T11:00:00+07:00') + 500 * 1000);
});

it('null when the forecast ends or has a gap; 0 for an empty span', () => {
  const hours = mkHours(START, [1, 1]);
  const from = at(START);
  expect(timeToDose(hours, from, 10000)).toBeNull();
  expect(doseBetween(hours, from, at('2026-09-29T13:00:00+07:00'))).toBeNull();
  const gap = [...mkHours(START, [5]), ...mkHours('2026-09-29T12:00:00+07:00', [5])];
  expect(doseBetween(gap, from, at('2026-09-29T12:30:00+07:00'))).toBeNull();
  expect(doseBetween(hours, from, from)).toBe(0);
});

it('sun status: fraction so far and the time of the 80 % warning', () => {
  const hours = mkHours(START, [10, 10, 10]);
  const s = sunStatus(hours, 'III', at(START), at('2026-09-29T10:10:00+07:00'));
  expect(s.fractionNow).toBeCloseTo((10 * 0.025 * 600) / 350, 6);
  expect(s.warnAt).toBe(at(START) + 1120 * 1000); // 280 J / 0.25 W
  const vi = sunStatus(hours, 'VI', at(START), at(START));
  expect(vi.warnAt).toBe(at(START) + 3200 * 1000); // VI: 0.8 x 1000 J at 0.25 W
  expect(vi.fractionNow).toBe(0);
  const low = sunStatus(mkHours(START, [1, 1, 1]), 'VI', at(START), at(START));
  expect(low.warnAt).toBeNull(); // 3 h at UVI 1 = 270 J/m2 < 800
});
