/**
 * Expo Go on Android: importing expo-notifications throws (57.0.21, module-level
 * `addPushTokenListener` -> "…removed from Expo Go with the release of SDK 53"). The app must
 * still open, say why there are no notifications, and keep the user's stored choices.
 */

import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { updateUserSettings } from '@/api/client';
import type { UserResponse } from '@/api/types';
import SettingsScreen from '@/app/settings';
import { SunSessionCard } from '@/components/SunSessionCard';
import {
  loadNotifications,
  notificationsAvailable,
  notificationsUnavailableReason,
  notifyUnavailableText,
  resetNotificationsForTests,
} from '@/lib/notifications';
import { DEFAULT_SETTINGS } from '@/lib/settings';
import { syncLocalNotifications } from '@/lib/useLocalNotifications';

import { mkHours } from './fixtures';
import { DEVICE, MemoryStorage, renderWithSettings } from './helpers';

// Node built-ins for the source scan (Jest runs in Node; the app has no @types/node)
type Dirent = { name: string; isDirectory(): boolean };
const fs = jest.requireActual('fs') as {
  readdirSync(dir: string, opts: { withFileTypes: true }): Dirent[];
  readFileSync(file: string, enc: 'utf8'): string;
};
const path = jest.requireActual('path') as {
  join(...parts: string[]): string;
  relative(from: string, to: string): string;
};
declare const __dirname: string;

jest.mock('@/api/client', () => {
  const actual = jest.requireActual('@/api/client');
  return { ...actual, createUser: jest.fn(), updateUserSettings: jest.fn(), deleteUser: jest.fn() };
});
const mockUpdate = updateUserSettings as jest.MockedFunction<typeof updateUserSettings>;

const EXPO_GO_ERROR =
  'expo-notifications: Android Push notifications (remote notifications) functionality provided ' +
  'by expo-notifications was removed from Expo Go with the release of SDK 53.';
const UNAVAILABLE = { mod: null, reason: 'expo-go-android' as const };
const at = (iso: string) => Date.parse(iso);
const HOURS = mkHours('2026-09-29T05:00:00+07:00', [
  0, 0.6, 2, 4, 6, 7.5, 9, 10, 10.2, 9.5, 7, 5.9, 4, 2, 0.8, 0, 0, 0, 0, 0, 0, 0, 0, 0,
]);

// the in-memory fake from jest.setup.ts (this file never replaces it)
const N = jest.requireMock('expo-notifications');
afterEach(() => resetNotificationsForTests());

describe('loading expo-notifications', () => {
  it('Expo Go on Android: the module is never required', () => {
    const requireModule = jest.fn(() => {
      throw new Error(EXPO_GO_ERROR);
    });
    const r = loadNotifications({ os: 'android', executionEnvironment: 'storeClient' }, requireModule);
    expect(r).toEqual({ mod: null, reason: 'expo-go-android' });
    expect(requireModule).not.toHaveBeenCalled();
    expect(notifyUnavailableText()).toMatch(/Expo Go บน Android ไม่รองรับการแจ้งเตือน/);
  });

  it('a module that throws at import is caught (load-failed), never rethrown', () => {
    const requireModule = jest.fn(() => {
      throw new Error(EXPO_GO_ERROR);
    });
    expect(() =>
      loadNotifications({ os: 'android', executionEnvironment: 'bare' }, requireModule),
    ).not.toThrow();
    expect(requireModule).toHaveBeenCalledTimes(1);
    expect(notificationsAvailable()).toBe(false);
    expect(notificationsUnavailableReason()).toBe('load-failed');
    expect(notifyUnavailableText()).toMatch(/โหลดระบบแจ้งเตือนของเครื่องไม่สำเร็จ/);
    loadNotifications({ os: 'android', executionEnvironment: 'bare' }, requireModule);
    expect(requireModule).toHaveBeenCalledTimes(1); // cached: never retried per call
  });

  it('web: not loaded and no reason shown; a build: loaded', () => {
    const requireModule = jest.fn(() => N);
    expect(loadNotifications({ os: 'web', executionEnvironment: null }, requireModule)).toEqual({
      mod: null,
      reason: 'web',
    });
    expect(notifyUnavailableText()).toBeNull();
    expect(requireModule).not.toHaveBeenCalled();
    resetNotificationsForTests();
    const r = loadNotifications({ os: 'android', executionEnvironment: 'bare' }, requireModule);
    expect(r).toEqual({ mod: N, reason: null });
  });

  it('only src/lib/notifications.ts loads expo-notifications (others: import type at most)', () => {
    const root = path.join(__dirname, '..', 'src');
    const offenders: string[] = [];
    const walk = (dir: string) => {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, e.name);
        if (e.isDirectory()) walk(p);
        else if (/\.(ts|tsx)$/.test(e.name)) {
          const code = fs.readFileSync(p, 'utf8');
          const value = /^\s*import\s+(?!type\b)[^;]*from\s+['"]expo-notifications['"]/m.test(code);
          const req = /require\(\s*['"]expo-notifications['"]\s*\)/.test(code);
          const bare = /^\s*import\s+['"]expo-notifications['"]/m.test(code);
          if ((value || req || bare) && !p.endsWith(path.join('lib', 'notifications.ts'))) {
            offenders.push(path.relative(root, p));
          }
        }
      }
    };
    walk(root);
    expect(offenders).toEqual([]);
  });
});

describe('without notifications', () => {
  beforeEach(() => {
    mockUpdate.mockReset();
    resetNotificationsForTests(UNAVAILABLE);
  });

  it('scheduling does nothing and never throws', async () => {
    N.scheduleNotificationAsync.mockClear();
    await expect(
      syncLocalNotifications(HOURS, { ...DEFAULT_SETTINGS, skinType: 'III' }, at('2026-09-29T05:30:00+07:00')),
    ).resolves.toBeUndefined();
    expect(N.scheduleNotificationAsync).not.toHaveBeenCalled();
  });

  it('settings: switches off and disabled on screen only; stored values and server untouched', async () => {
    const storage = new MemoryStorage({
      skinType: 'III',
      userId: 7,
      deviceId: DEVICE,
      serverConsent: true,
      notifyEnabled: true,
      dailySummary: true,
      reapplyReminder: true,
    });
    const user: UserResponse = {
      id: 7,
      skin_type: 'III',
      province: null,
      notify_enabled: true,
      alert_threshold: 11,
      safe_threshold: 9,
      alert_burn_minutes: 30,
      updated_at: '2026-09-29T06:00:00+00:00',
      disclaimer: 'd',
    };
    mockUpdate.mockResolvedValue(user);
    await renderWithSettings(<SettingsScreen />, storage);
    await screen.findByTestId('settings-skin', {}, { timeout: 5000 });
    expect(screen.getByTestId('notify-unavailable')).toHaveTextContent(/development build/);
    expect(screen.getByTestId('notify-unavailable')).toHaveTextContent(/จะถึง 80 % ราวกี่โมง/);
    for (const id of ['notify-switch', 'daily-switch', 'reapply-switch']) {
      const sw = screen.getByTestId(id);
      expect(sw.props.value).toBe(false);
      expect(sw.props.disabled).toBe(true);
    }
    expect(screen.queryByTestId('notify-not-allowed')).toBeNull();
    // even if a disabled switch still fired, nothing is stored or synced
    await fireEvent(screen.getByTestId('notify-switch'), 'valueChange', false);
    await fireEvent(screen.getByTestId('daily-switch'), 'valueChange', false);
    expect(mockUpdate).not.toHaveBeenCalled(); // opening the screen syncs nothing
    expect(storage.stored()).toMatchObject({
      notifyEnabled: true,
      dailySummary: true,
      reapplyReminder: true,
    });
    // a real server change still sends the user's stored notify_enabled (true), never false
    await fireEvent.press(screen.getByTestId('threshold-11'));
    await waitFor(() => expect(mockUpdate).toHaveBeenCalled());
    expect(mockUpdate.mock.calls[0][2]).toMatchObject({ notify_enabled: true });
    expect(storage.stored()?.notifyEnabled).toBe(true);
  });

  it('SunSessionCard shows the 80 % time on screen and does not promise a notification', async () => {
    const DAY_NOW = at('2026-09-29T11:00:00+07:00');
    const storage = new MemoryStorage({ skinType: 'III', sunStartedAt: DAY_NOW });
    await renderWithSettings(
      <SunSessionCard hours={HOURS} skin="III" isDaylight nowMs={DAY_NOW} />,
      storage,
    );
    expect(await screen.findByTestId('notify-unavailable')).toHaveTextContent(/ต้องเปิดแอปดูเอง/);
    expect(screen.getByTestId('sun-warn-at')).toHaveTextContent(
      'จะถึงประมาณ 80 % ของ MED ราว 11:20 (ไม่มีแจ้งเตือนเด้ง ดูที่หน้านี้)',
    );
    expect(screen.getByTestId('sun-status')).toHaveTextContent(/ได้รับ UV แล้วประมาณ \d+ % ของ/);
    expect(screen.queryByText(/จะเตือนราว/)).toBeNull();
    expect(screen.queryByTestId('notify-not-allowed')).toBeNull();
  });
});
