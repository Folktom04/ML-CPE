import { fireEvent, render, screen } from '@testing-library/react-native';

import { ApiError, fetchPredict } from '@/api/client';
import HomeScreen from '@/app/index';
import { DISCLAIMER_TH } from '@/config';

import { samplePredict } from './fixtures';

jest.mock('@/api/client', () => {
  const actual = jest.requireActual('@/api/client');
  return { ...actual, fetchPredict: jest.fn() };
});
const mockFetch = fetchPredict as jest.MockedFunction<typeof fetchPredict>;

beforeEach(() => mockFetch.mockReset());

it('loads /predict for Pathum Thani, skin type III, and shows both cards', async () => {
  mockFetch.mockResolvedValue(samplePredict());
  await render(<HomeScreen />);
  expect(await screen.findByTestId('uvi-value', {}, { timeout: 5000 })).toHaveTextContent('5.5');
  expect(screen.getByTestId('burn-value')).toHaveTextContent('35 นาที');
  expect(mockFetch).toHaveBeenCalledWith({ lat: 14.02, lon: 100.52, skin_type: 'III' });
  expect(screen.getByTestId('disclaimer')).toHaveTextContent(samplePredict().disclaimer);
});

it('shows the Thai error, keeps the disclaimer and retries', async () => {
  mockFetch.mockRejectedValueOnce(
    new ApiError('ข้อมูลสภาพอากาศของชั่วโมงนี้ยังไม่มา', {
      status: 503,
      url: 'http://192.168.1.48:8000/predict',
      detail: 'HTTP 503: Open-Meteo data for the current hour is missing',
    }),
  );
  await render(<HomeScreen />);
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
