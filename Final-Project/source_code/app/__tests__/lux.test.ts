import { formatLux, medianLux, pushLux, type LuxSample } from '@/lib/lux';

it('median is robust to a single spike', () => {
  const s: LuxSample[] = [100, 110, 90, 50000, 105].map((lux, i) => ({ lux, t: i * 0.25 }));
  expect(medianLux(s)).toBe(105);
  expect(medianLux(s.slice(0, 4))).toBe(105); // even count: mean of the middle two
  expect(medianLux([])).toBeNull();
});

it('keeps only the last 2 s and skips invalid values', () => {
  let s: LuxSample[] = [];
  s = pushLux(s, { lux: 10, t: 0 });
  s = pushLux(s, { lux: NaN, t: 0.5 });
  s = pushLux(s, { lux: -1, t: 1 });
  s = pushLux(s, { lux: 20, t: 1.5 });
  expect(s.map((x) => x.lux)).toEqual([10, 20]);
  s = pushLux(s, { lux: 30, t: 2.6 }); // t=0 is now older than 2 s
  expect(s.map((x) => x.lux)).toEqual([20, 30]);
});

it('formats whole lux with a thousands separator', () => {
  expect(formatLux(32767.6)).toBe('32,768 lux');
  expect(formatLux(0)).toBe('0 lux');
});
