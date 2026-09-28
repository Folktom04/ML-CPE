import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import * as Location from 'expo-location';
import { Redirect } from 'expo-router';

import { ApiError, fetchForecast, fetchPredict } from '@/api/client';
import HomeScreen from '@/app/index';
import { DISCLAIMER_TH } from '@/config';

import { sampleHours, sampleNight, samplePredict } from './fixtures';
import { MemoryStorage, renderWithSettings } from './helpers';

/** A user who finished onboarding (default location: Pathum Thani). */
const onboarded = () => new MemoryStorage({ onboarded: true });

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
  await renderWithSettings(<HomeScreen />, onboarded());
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
  await renderWithSettings(<HomeScreen />, onboarded());
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
  await renderWithSettings(<HomeScreen />, onboarded());
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
  await renderWithSettings(<HomeScreen />, onboarded());
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
  await renderWithSettings(<HomeScreen />, new MemoryStorage({ skinType: 'V', onboarded: true }));
  expect(await screen.findByTestId('uvi-value', {}, { timeout: 5000 })).toBeTruthy();
  expect(mockFetch).toHaveBeenCalledWith({ lat: 14.02, lon: 100.52, skin_type: 'V' });
  expect(screen.getAllByTestId(/^bar-\d+$/)).toHaveLength(4); // now + 3 forecast hours
  expect(screen.getByText(/ผิวประเภท V/)).toBeTruthy();
  expect(screen.queryByTestId('quiz-prompt')).toBeNull();
});

it('asks for the quiz while no skin type is stored (type III meanwhile)', async () => {
  mockFetch.mockResolvedValue(samplePredict());
  await renderWithSettings(<HomeScreen />, onboarded());
  expect(await screen.findByTestId('quiz-prompt', {}, { timeout: 5000 })).toHaveTextContent(
    /แบบสอบถาม 5 ข้อ/,
  );
  expect(mockFetch).toHaveBeenCalledWith({ lat: 14.02, lon: 100.52, skin_type: 'III' });
});

it('links to the sky camera everywhere and to the light meter only on Android', async () => {
  const { Platform } = jest.requireActual('react-native');
  mockFetch.mockResolvedValue(samplePredict());
  const view = await renderWithSettings(<HomeScreen />, onboarded());
  await screen.findByTestId('uvi-value', {}, { timeout: 5000 });
  expect(screen.getByTestId('open-camera')).toBeTruthy();
  expect(screen.queryByTestId('open-light')).toBeNull(); // jest-expo runs as iOS
  await view.unmount();
  jest.replaceProperty(Platform, 'OS', 'android');
  await renderWithSettings(<HomeScreen />, onboarded());
  await screen.findByTestId('uvi-value', {}, { timeout: 5000 });
  expect(screen.getByTestId('open-light')).toBeTruthy();
  jest.restoreAllMocks();
});

describe('location (day 21)', () => {
  const L = jest.mocked(Location);

  beforeEach(() => {
    jest.mocked(Redirect).mockClear();
    L.getCurrentPositionAsync.mockClear();
    L.getForegroundPermissionsAsync.mockResolvedValue({ status: 'granted' } as never);
    L.getLastKnownPositionAsync.mockResolvedValue(null);
    L.getCurrentPositionAsync.mockResolvedValue({
      coords: { latitude: 13.75634, longitude: 100.50177 },
    } as never);
  });

  it('a first-time user is sent to onboarding and nothing is fetched', async () => {
    await renderWithSettings(<HomeScreen />, new MemoryStorage());
    await waitFor(() => expect(Redirect).toHaveBeenCalled());
    expect(jest.mocked(Redirect).mock.calls[0][0]).toEqual({ href: '/onboarding' });
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('GPS: /predict gets the fix rounded to 0.01 deg and the nearest province is kept', async () => {
    mockFetch.mockResolvedValue(samplePredict());
    const storage = new MemoryStorage({ onboarded: true, locationMode: 'gps' });
    await renderWithSettings(<HomeScreen />, storage);
    expect(await screen.findByTestId('uvi-value', {}, { timeout: 5000 })).toBeTruthy();
    expect(mockFetch).toHaveBeenCalledWith({ lat: 13.76, lon: 100.5, skin_type: 'III' });
    expect(screen.getByTestId('place-label')).toHaveTextContent(
      /^ตำแหน่งปัจจุบัน \(GPS\) · ใกล้ จ\.กรุงเทพมหานคร · ผิวประเภท III$/,
    );
    await waitFor(() => expect(storage.stored()?.province).toBe('กรุงเทพมหานคร'));
    expect(JSON.stringify(storage.stored())).not.toMatch(/13\.7|100\.5/); // no GPS stored
    expect(mockFetch).toHaveBeenCalledTimes(1); // keeping the province does not reload
  });

  it('GPS permission denied later: uses the chosen/last province and says why', async () => {
    L.getForegroundPermissionsAsync.mockResolvedValue({ status: 'denied' } as never);
    mockFetch.mockResolvedValue(samplePredict());
    const storage = new MemoryStorage({ onboarded: true, locationMode: 'gps', province: 'ลำปาง' });
    await renderWithSettings(<HomeScreen />, storage);
    expect(await screen.findByTestId('place-notice', {}, { timeout: 5000 })).toHaveTextContent(
      /ไม่ได้รับสิทธิ์ตำแหน่ง จึงใช้จ\.ลำปางแทน/,
    );
    const lampang = mockFetch.mock.calls[0][0];
    expect(lampang.lat).toBeCloseTo(18.29, 1);
    expect(lampang.lon).toBeCloseTo(99.49, 1);
  });

  it('a chosen province: its capital is used and the far-away note from the API is shown', async () => {
    const note = 'ความแม่นยำนอกพื้นที่ปทุมธานียังไม่ได้ประเมิน';
    mockFetch.mockResolvedValue(samplePredict({ note }));
    const storage = new MemoryStorage({
      onboarded: true,
      locationMode: 'province',
      province: 'เชียงใหม่',
    });
    await renderWithSettings(<HomeScreen />, storage);
    expect(await screen.findByText(note, {}, { timeout: 5000 })).toBeTruthy();
    expect(mockFetch).toHaveBeenCalledWith({ lat: 18.79, lon: 98.98, skin_type: 'III' });
    expect(screen.getByTestId('place-label')).toHaveTextContent(/^จ\.เชียงใหม่ \(เลือกเอง\) · ผิวประเภท III$/);
    expect(L.getCurrentPositionAsync).not.toHaveBeenCalled();
  });

  it('outside Thailand the Thai 422 message from the API is shown', async () => {
    mockFetch.mockRejectedValue(
      new ApiError('รองรับเฉพาะพื้นที่ประเทศไทย', { status: 422, detail: 'HTTP 422: รองรับเฉพาะพื้นที่ประเทศไทย' }),
    );
    L.getCurrentPositionAsync.mockResolvedValue({
      coords: { latitude: 35.68, longitude: 139.69 },
    } as never);
    await renderWithSettings(<HomeScreen />, new MemoryStorage({ onboarded: true, locationMode: 'gps' }));
    expect(await screen.findByTestId('error-message', {}, { timeout: 5000 })).toHaveTextContent(
      'รองรับเฉพาะพื้นที่ประเทศไทย',
    );
  });
});

it('day 22: after loading, local notifications are scheduled from the forecast', async () => {
  const N = jest.requireMock('expo-notifications');
  N.__reset();
  N.getPermissionsAsync.mockResolvedValue({ granted: true, canAskAgain: true });
  const now = Date.now();
  const startIso = new Date(Math.floor(now / 3600e3) * 3600e3 + 7 * 3600e3)
    .toISOString()
    .slice(0, 19);
  // the next 5 hours all at alert_uvi 9.8 in daytime -> one "UV high" in the next hour
  const forecast = sampleHours(`${startIso}+07:00`, [9, 9, 9, 9, 9, 9]).slice(1);
  mockFetch.mockResolvedValue(
    samplePredict({ time: `${startIso}+07:00`, uvi: 2, alert_uvi: 2.5, forecast }),
  );
  await renderWithSettings(<HomeScreen />, new MemoryStorage({ onboarded: true, skinType: 'III' }));
  await waitFor(() => expect(N.scheduleNotificationAsync).toHaveBeenCalled());
  const kinds = N.scheduleNotificationAsync.mock.calls.map(
    (c: [{ content: { data: { kind: string } } }]) => c[0].content.data.kind,
  );
  expect(kinds).toContain('uv_high');
  expect(kinds.some((k: string) => k.startsWith('daily'))).toBe(true);
});
