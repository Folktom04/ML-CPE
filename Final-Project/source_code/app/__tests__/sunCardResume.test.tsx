/**
 * Field test 4 Oct 2026: after the lock screen the "อยู่กลางแจ้ง" card still showed 79 % at 10:33
 * (the value of its last 60 s tick before the screen locked) instead of about 87 %, because JS
 * timers pause in the background and nothing refreshed the clock when the app became active.
 */
import { act, screen } from '@testing-library/react-native';
import { AppState, type AppStateStatus } from 'react-native';

import { SunSessionCard } from '@/components/SunSessionCard';

import { mkHours } from './fixtures';
import { MemoryStorage, renderWithSettings } from './helpers';

const at = (iso: string) => Date.parse(iso);
const FLAT = mkHours('2026-10-04T06:00:00+07:00', Array(12).fill(8.1));
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

describe('SunSessionCard after the lock screen', () => {
  it('shows the dose of now (87 %), not of the last tick before locking (79 %)', async () => {
    let now = at('2026-10-04T10:30:50+07:00'); // last tick before the screen locked
    jest.spyOn(Date, 'now').mockImplementation(() => now);
    await renderWithSettings(
      <SunSessionCard hours={FLAT} skin="III" isDaylight />,
      new MemoryStorage({ skinType: 'III', sunStartedAt: START }),
    );
    expect(await screen.findByTestId('sun-status')).toHaveTextContent(/ได้รับ UV แล้วประมาณ 79 %/);

    now = at('2026-10-04T10:33:00+07:00'); // 25 min x 60 x 8.1 x 0.025 / 350 = 87 %
    expect(handlers.length).toBeGreaterThan(0);
    await act(async () => handlers.forEach((h) => h('active')));
    expect(screen.getByTestId('sun-status')).toHaveTextContent(/ได้รับ UV แล้วประมาณ 87 %/);
    expect(screen.getByTestId('sun-warn-at')).toHaveTextContent(/ถึง 80 % แล้วโดยประมาณ/);
  });
});
