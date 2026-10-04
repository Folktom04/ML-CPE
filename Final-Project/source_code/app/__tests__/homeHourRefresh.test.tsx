/**
 * Field test 4 Oct 2026: at 12:00 the home screen still said "ดัชนี UV ตอนนี้ (11:00–12:00 น.)".
 * /predict answers for the clock hour of the request and the screen fetched it only on opening
 * or pull-to-refresh, so it must fetch again once the clock hour has changed (checked every 30 s
 * and when the app comes back to the foreground).
 */
import { act, screen, waitFor } from '@testing-library/react-native';
import { AppState, type AppStateStatus } from 'react-native';

import { fetchForecast, fetchPredict } from '@/api/client';
import HomeScreen from '@/app/index';
import { hourChanged } from '@/lib/useNow';

import { samplePredict } from './fixtures';
import { MemoryStorage, renderWithSettings } from './helpers';

jest.mock('@/api/client', () => {
  const actual = jest.requireActual('@/api/client');
  return { ...actual, fetchPredict: jest.fn(), fetchForecast: jest.fn() };
});
const mockFetch = fetchPredict as jest.MockedFunction<typeof fetchPredict>;
const mockForecast = fetchForecast as jest.MockedFunction<typeof fetchForecast>;

const at = (iso: string) => Date.parse(iso);
let now = 0;
let handlers: ((s: AppStateStatus) => void)[] = [];

beforeEach(() => {
  mockFetch.mockReset();
  mockForecast.mockReset();
  handlers = [];
  jest.spyOn(Date, 'now').mockImplementation(() => now);
  jest.spyOn(AppState, 'addEventListener').mockImplementation((_type, h) => {
    handlers.push(h as (s: AppStateStatus) => void);
    return { remove: () => undefined } as ReturnType<typeof AppState.addEventListener>;
  });
});

afterEach(() => jest.restoreAllMocks());

const backToForeground = () => act(async () => handlers.forEach((h) => h('active')));

describe('hourChanged', () => {
  it('compares clock hours (Bangkok hours start on UTC hours, +7 h)', () => {
    expect(hourChanged(at('2026-10-04T11:00:00+07:00'), at('2026-10-04T11:59:59+07:00'))).toBe(false);
    expect(hourChanged(at('2026-10-04T11:59:59+07:00'), at('2026-10-04T12:00:00+07:00'))).toBe(true);
    expect(hourChanged(at('2026-10-04T12:00:00+07:00'), at('2026-10-04T11:30:00+07:00'))).toBe(false);
  });
});

describe('home screen current hour', () => {
  it('fetches /predict again after the clock hour changes and shows the new hour', async () => {
    now = at('2026-10-04T11:58:00+07:00');
    mockFetch.mockResolvedValueOnce(samplePredict({ time: '2026-10-04T11:00:00+07:00', uvi: 8.0 }));
    mockFetch.mockResolvedValueOnce(samplePredict({ time: '2026-10-04T12:00:00+07:00', uvi: 8.6 }));
    await renderWithSettings(<HomeScreen />, new MemoryStorage({ onboarded: true }));
    expect(await screen.findByText(/ดัชนี UV ตอนนี้ \(11:00–12:00 น\.\)/)).toBeTruthy();

    now = at('2026-10-04T12:03:00+07:00'); // back from the lock screen in the next hour
    await backToForeground();
    expect(await screen.findByText(/ดัชนี UV ตอนนี้ \(12:00–13:00 น\.\)/)).toBeTruthy();
    expect(screen.getByTestId('uvi-value')).toHaveTextContent('8.6');
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('does not fetch again within the same clock hour', async () => {
    now = at('2026-10-04T11:10:00+07:00');
    mockFetch.mockResolvedValue(samplePredict({ time: '2026-10-04T11:00:00+07:00' }));
    await renderWithSettings(<HomeScreen />, new MemoryStorage({ onboarded: true }));
    expect(await screen.findByText(/ดัชนี UV ตอนนี้ \(11:00–12:00 น\.\)/)).toBeTruthy();
    now = at('2026-10-04T11:50:00+07:00');
    await backToForeground();
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});

describe('automatic hour refresh fails', () => {
  const NOTE = 'อัปเดตชั่วโมงใหม่ไม่สำเร็จ · ลากลงเพื่อลองใหม่';
  const at11 = () => samplePredict({ time: '2026-10-04T11:00:00+07:00', uvi: 8.0 });

  async function openAt1158() {
    now = at('2026-10-04T11:58:00+07:00');
    mockFetch.mockResolvedValueOnce(at11());
    await renderWithSettings(<HomeScreen />, new MemoryStorage({ onboarded: true }));
    expect(await screen.findByText(/ดัชนี UV ตอนนี้ \(11:00–12:00 น\.\)/)).toBeTruthy();
  }

  it('keeps the old values with a note, and does not call the old hour "ตอนนี้"', async () => {
    await openAt1158();
    mockFetch.mockRejectedValue(new Error('Network request failed'));
    now = at('2026-10-04T12:03:00+07:00');
    await backToForeground();
    expect(await screen.findByText(NOTE)).toBeTruthy();
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId('uvi-value')).toHaveTextContent('8.0'); // old data still shown
    expect(screen.queryByText('โหลดข้อมูลไม่สำเร็จ')).toBeNull(); // no full-screen error
    expect(screen.queryByText(/ดัชนี UV ตอนนี้/)).toBeNull();
    expect(screen.getByText(/11:00–12:00 น\./)).toBeTruthy(); // the real hour of the data
  });

  it('retries at most 3 times per hour, at least 2 min apart', async () => {
    await openAt1158();
    mockFetch.mockRejectedValue(new Error('Network request failed'));
    const visit = async (iso: string) => {
      now = at(iso);
      await backToForeground();
    };
    await visit('2026-10-04T12:03:00+07:00'); // attempt 1
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
    await visit('2026-10-04T12:04:30+07:00'); // 1.5 min later: too soon
    await visit('2026-10-04T12:05:00+07:00'); // attempt 2 (2 min after attempt 1)
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(3));
    await visit('2026-10-04T12:06:00+07:00'); // too soon
    await visit('2026-10-04T12:07:30+07:00'); // attempt 3
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(4));
    await visit('2026-10-04T12:20:00+07:00'); // 3 attempts used in this hour
    await visit('2026-10-04T12:50:00+07:00');
    expect(mockFetch).toHaveBeenCalledTimes(4);
    await visit('2026-10-04T13:01:00+07:00'); // a new hour: may try again
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(5));
    expect(screen.getByTestId('uvi-value')).toHaveTextContent('8.0');
  });
});
