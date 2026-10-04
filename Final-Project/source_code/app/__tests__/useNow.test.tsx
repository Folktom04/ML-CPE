/**
 * Field test 4 Oct 2026: after the lock screen the "อยู่กลางแจ้ง" card still showed 79 % at 10:33
 * (the value of its last 60 s tick before the screen locked) instead of about 87 %, because JS
 * timers pause in the background and nothing refreshed the clock when the app became active.
 */
import { act, renderHook } from '@testing-library/react-native';
import { AppState, type AppStateStatus } from 'react-native';

import { NOW_INTERVAL_MS, useNow } from '@/lib/useNow';

const at = (iso: string) => Date.parse(iso);
const START = at('2026-10-04T10:08:00+07:00');

let handlers: ((s: AppStateStatus) => void)[] = [];
let removed = 0;

beforeEach(() => {
  handlers = [];
  removed = 0;
  jest.spyOn(AppState, 'addEventListener').mockImplementation((_type, h) => {
    handlers.push(h as (s: AppStateStatus) => void);
    return {
      remove: () => {
        removed += 1;
      },
    } as ReturnType<typeof AppState.addEventListener>;
  });
});

afterEach(() => {
  jest.restoreAllMocks();
  jest.useRealTimers();
});

describe('useNow', () => {
  it('ticks on its interval', async () => {
    jest.useFakeTimers({ now: START });
    const { result } = await renderHook(() => useNow());
    expect(result.current).toBe(START);
    await act(async () => {
      jest.advanceTimersByTime(NOW_INTERVAL_MS);
    });
    expect(result.current).toBe(START + NOW_INTERVAL_MS);
  });

  it('refreshes at once when the app becomes active, and cleans up on unmount', async () => {
    jest.useFakeTimers({ now: START });
    const { result, unmount } = await renderHook(() => useNow());
    jest.setSystemTime(START + 25 * 60 * 1000); // back from the lock screen, no tick ran
    await act(async () => handlers.forEach((h) => h('active')));
    expect(result.current).toBe(START + 25 * 60 * 1000);
    await unmount();
    expect(removed).toBe(1);
  });

  it('does nothing when a fixed clock is given (tests)', async () => {
    const { result } = await renderHook(() => useNow(NOW_INTERVAL_MS, 123));
    expect(result.current).toBe(123);
    expect(handlers).toHaveLength(0);
  });
});
