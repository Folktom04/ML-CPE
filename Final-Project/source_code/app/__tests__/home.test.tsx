import { fireEvent, screen } from '@testing-library/react-native';

import { ApiError, fetchForecast, fetchPredict } from '@/api/client';
import HomeScreen from '@/app/index';
import { DISCLAIMER_TH } from '@/config';

import { sampleHours, sampleNight, samplePredict } from './fixtures';
import { MemoryStorage, renderWithSettings } from './helpers';

jest.mock('@/api/client', () => {
  const actual = jest.requireActual('@/api/client');
  return { ...actual, fetchPredict: jest.fn(), fetchForecast: jest.fn() };
});
const mockFetch = fetchPredict as jest.MockedFunction<typeof fetchPredict>;
const mockForecast = fetchForecast as jest.MockedFunction<typeof fetchForecast>;

beforeEach(() => {
  mockFetch.mockReset();
  mockForecast.mockReset();
});

it('loads /predict for Pathum Thani, skin type III, and shows both cards', async () => {
  mockFetch.mockResolvedValue(samplePredict());
  await renderWithSettings(<HomeScreen />);
  expect(await screen.findByTestId('uvi-value', {}, { timeout: 5000 })).toHaveTextContent('5.5');
  expect(screen.getByTestId('burn-value')).toHaveTextContent('35 นาที');
  expect(mockFetch).toHaveBeenCalledWith({ lat: 14.02, lon: 100.52, skin_type: 'III' });
  expect(screen.getByTestId('disclaimer')).toHaveTextContent(samplePredict().disclaimer);
  expect(mockForecast).not.toHaveBeenCalled(); // daytime: no extra request
});

it('shows the Thai error, keeps the disclaimer and retries', async () => {
  mockFetch.mockRejectedValueOnce(
    new ApiError('ข้อมูลสภาพอากาศของชั่วโมงนี้ยังไม่มา', {
      status: 503,
      url: 'http://192.168.1.48:8000/predict',
      detail: 'HTTP 503: Open-Meteo data for the current hour is missing',
    }),
  );
  await renderWithSettings(<HomeScreen />);
  expect(await screen.findByTestId('error-message', {}, { timeout: 5000 })).toHaveTextContent(
    'ข้อมูลสภาพอากาศของชั่วโมงนี้ยังไม่มา',
  );
  expect(screen.getByTestId('error-url')).toHaveTextContent(
    'ที่อยู่ที่เรียก: http://192.168.1.48:8000/predict',
  );
  expect(screen.getByTestId('error-detail')).toHaveTextContent(
    'รายละเอียด: HTTP 503: Open-Meteo data for the current hour is missing',
  );
  expect(screen.getByTestId('disclaimer')).toHaveTextContent(DISCLAIMER_TH);
  mockFetch.mockResolvedValueOnce(samplePredict());
  await fireEvent.press(screen.getByText('ลองใหม่'));
  expect(await screen.findByTestId('uvi-value')).toBeTruthy();
  expect(mockFetch).toHaveBeenCalledTimes(2);
});

it("at night fetches /forecast and shows tomorrow's peak instead of the advice", async () => {
  mockFetch.mockResolvedValue(sampleNight());
  // 20:00 tonight: 14 dark hours, then 10:00-12:00 tomorrow (peak 7.8 at 11:00)
  const hours = sampleHours('2026-09-27T20:00:00+07:00', [...Array(14).fill(0), 3.1, 7.8, 5.2, 0]);
  mockForecast.mockResolvedValue({ lat: 14.02, lon: 100.52, hours, note: null, disclaimer: 'd' });
  await renderWithSettings(<HomeScreen />);
  const box = await screen.findByTestId('next-peak', {}, { timeout: 5000 });
  expect(box).toHaveTextContent(/พรุ่งนี้ UV สูงสุดประมาณ/);
  expect(box).toHaveTextContent(/7\.8/);
  expect(box).toHaveTextContent(/ราว 11:00 น\./);
  expect(mockForecast).toHaveBeenCalledWith(14.02, 100.52, 36);
  expect(screen.queryByText(/แว่นกันแดด/)).toBeNull();
});

it('at night a failed /forecast does not break the page', async () => {
  mockFetch.mockResolvedValue(sampleNight());
  mockForecast.mockRejectedValue(
    new ApiError('ดึงข้อมูลสภาพอากาศจาก Open-Meteo ไม่ได้', { status: 502 }),
  );
  await renderWithSettings(<HomeScreen />);
  expect(await screen.findByTestId('next-peak', {}, { timeout: 5000 })).toHaveTextContent(
    'ยังไม่มีข้อมูลพยากรณ์ของวันถัดไป',
  );
  expect(screen.getByTestId('uvi-value')).toBeTruthy();
  expect(screen.queryByTestId('error-message')).toBeNull();
});

it('uses the stored skin type and draws the hourly chart', async () => {
  mockFetch.mockResolvedValue(
    samplePredict({ forecast: sampleHours('2026-09-27T14:00:00+07:00', [6.1, 4.2, 1.0]) }),
  );
  await renderWithSettings(<HomeScreen />, new MemoryStorage({ skinType: 'V' }));
  expect(await screen.findByTestId('uvi-value', {}, { timeout: 5000 })).toBeTruthy();
  expect(mockFetch).toHaveBeenCalledWith({ lat: 14.02, lon: 100.52, skin_type: 'V' });
  expect(screen.getAllByTestId(/^bar-\d+$/)).toHaveLength(4); // now + 3 forecast hours
  expect(screen.getByText(/ผิวประเภท V/)).toBeTruthy();
  expect(screen.queryByTestId('quiz-prompt')).toBeNull();
});

it('asks for the quiz while no skin type is stored (type III meanwhile)', async () => {
  mockFetch.mockResolvedValue(samplePredict());
  await renderWithSettings(<HomeScreen />);
  expect(await screen.findByTestId('quiz-prompt', {}, { timeout: 5000 })).toHaveTextContent(
    /แบบสอบถาม 5 ข้อ/,
  );
  expect(mockFetch).toHaveBeenCalledWith({ lat: 14.02, lon: 100.52, skin_type: 'III' });
});
