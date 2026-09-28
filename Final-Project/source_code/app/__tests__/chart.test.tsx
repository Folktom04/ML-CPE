import { fireEvent, render, screen } from '@testing-library/react-native';

import { HourlyChart } from '@/components/HourlyChart';
import {
  chartHours,
  hourTick,
  initialFocusIndex,
  MIN_Y_MAX,
  peakIndex,
  scaleY,
  scrollOffsetFor,
  yMax,
} from '@/lib/chart';
import { WHO_COLORS } from '@/lib/uv';

import { sampleHours, samplePredict } from './fixtures';

const NOW = '2026-09-27T13:00:00+07:00';

it('puts the current hour first, then only later forecast hours', () => {
  const data = samplePredict({
    forecast: sampleHours('2026-09-27T13:00:00+07:00', [5.5, 4.0, 2.1]), // 13:00 is "now"
  });
  const hours = chartHours(data);
  expect(hours.map((h) => h.time.slice(11, 16))).toEqual(['13:00', '14:00', '15:00']);
  expect(hours[0]).toMatchObject({ uvi: 5.49, uvi_range: [4.94, 6.66], level: 'ปานกลาง' });
});

it('y-axis: at least 12, else the highest q90 rounded up to an even number', () => {
  expect(yMax(sampleHours(NOW, [0, 3, 5]))).toBe(MIN_Y_MAX);
  const high = sampleHours(NOW, [12.5]); // q90 = 13.3
  expect(yMax(high)).toBe(14);
  expect(yMax([])).toBe(MIN_Y_MAX);
});

it('scales and clips values to the plot', () => {
  expect(scaleY(6, 12, 120)).toBe(60);
  expect(scaleY(20, 12, 120)).toBe(120);
  expect(scaleY(-1, 12, 120)).toBe(0);
  expect(scaleY(NaN, 12, 120)).toBe(0);
});

it('finds the peak and labels every 3rd hour plus the first column', () => {
  expect(peakIndex(sampleHours(NOW, [1, 7, 7, 3]))).toBe(1);
  expect(peakIndex([])).toBe(-1);
  expect(hourTick('2026-09-27T13:00:00+07:00', 0)).toBe('13');
  expect(hourTick('2026-09-27T14:00:00+07:00', 1)).toBeNull();
  expect(hourTick('2026-09-27T15:00:00+07:00', 2)).toBe('15');
});

it('draws one column per hour, labels only the peak, and shows a tapped hour', async () => {
  const hours = sampleHours(NOW, [5.5, 7.9, 6.2, 3.0, 0.4, 0, 0]);
  await render(<HourlyChart hours={hours} isDaylight />);
  expect(screen.getAllByTestId(/^bar-\d+$/)).toHaveLength(7);
  expect(screen.getAllByTestId('peak-label')).toHaveLength(1);
  expect(screen.getByTestId('peak-label')).toHaveTextContent('7.9');
  expect(screen.getByTestId('chart-detail')).toHaveTextContent(/ตอนนี้ 13:00–14:00 · UVI 5\.5/);
  await fireEvent.press(screen.getByTestId('bar-1'));
  expect(screen.getByTestId('chart-detail')).toHaveTextContent(
    '14:00–15:00 · UVI 7.9 (7.4–8.7) · สูงมาก',
  );
  expect(screen.getByTestId('chart-summary')).toHaveTextContent(/สูงสุด 7\.9 \(สูงมาก\) เวลา 14:00/);
  expect(screen.getByLabelText('14:00–15:00 UVI 7.9 ระดับสูงมาก')).toBeTruthy();
  // gridlines at the WHO boundaries 3, 6, 8, 11 (axis top 12)
  ['3', '6', '8', '11'].forEach((g) => expect(screen.getByTestId(`grid-${g}`)).toBeTruthy());
});

it('says so when there is no forecast', async () => {
  await render(<HourlyChart hours={[]} isDaylight={false} />);
  expect(screen.getByText('ยังไม่มีข้อมูลพยากรณ์')).toBeTruthy();
});

// 20:00 tonight: 10 dark hours, then 06:00-11:00 tomorrow (peak 8.3 at 10:00), then night
const NIGHT = sampleHours('2026-09-27T20:00:00+07:00', [
  ...Array(10).fill(0),
  0.4,
  2.0,
  4.5,
  6.9,
  8.3,
  7.1,
  0,
]);

it('opens on now in daytime, and on the next daytime peak at night', () => {
  expect(initialFocusIndex(sampleHours(NOW, [5, 6, 7]), true)).toBe(0);
  expect(initialFocusIndex(NIGHT, false)).toBe(14);
  expect(initialFocusIndex(sampleHours(NOW, [0, 0, 0]), false)).toBe(0); // no daytime ahead
  expect(initialFocusIndex([], false)).toBe(0);
});

it('scroll offset centres the column and stays inside the content', () => {
  expect(scrollOffsetFor(0, 26, 300, 25)).toBe(0);
  expect(scrollOffsetFor(14, 26, 300, 25)).toBe(14 * 26 + 13 - 150);
  expect(scrollOffsetFor(24, 26, 300, 25)).toBe(25 * 26 - 300); // clamped at the end
  expect(scrollOffsetFor(3, 26, 1000, 25)).toBe(0); // everything fits
});

it("at night selects tomorrow's peak and marks it with a dot, not a background", async () => {
  await render(<HourlyChart hours={NIGHT} isDaylight={false} />);
  expect(screen.getByTestId('chart-detail')).toHaveTextContent(
    /^พรุ่งนี้ 10:00–11:00 · UVI 8\.3 .* · สูงมาก/,
  );
  expect(screen.getAllByTestId('selected-marker')).toHaveLength(1);
  const slot = screen.getByTestId('bar-14');
  expect(slot).toHaveStyle({ width: 26 });
  expect(slot).not.toHaveStyle({ backgroundColor: expect.anything() });
  expect(screen.getByTestId('bar-14').props.accessibilityState).toEqual({ selected: true });
  await fireEvent.press(screen.getByTestId('bar-0'));
  expect(screen.getByTestId('chart-detail')).toHaveTextContent(/^ตอนนี้ 20:00–21:00/);
  expect(screen.getAllByTestId('selected-marker')).toHaveLength(1);
});

it('colours a 7.8 hour red (สูงมาก), like the main card and risk.py', async () => {
  const hours = sampleHours(NOW, [7.8, 7.49]);
  expect(hours.map((h) => h.level)).toEqual(['สูงมาก', 'สูง']);
  await render(<HourlyChart hours={hours} isDaylight />);
  expect(screen.getByTestId('bar-fill-0')).toHaveStyle({ backgroundColor: WHO_COLORS[3] });
  expect(screen.getByTestId('bar-fill-1')).toHaveStyle({ backgroundColor: WHO_COLORS[2] });
});
