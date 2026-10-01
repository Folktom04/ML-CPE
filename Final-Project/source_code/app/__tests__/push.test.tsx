/**
 * Day 23: server push on the app side. Plan items 1-27: getPushToken, the pushActive conditions
 * (a)-(e), no double alerts with local notifications, consent / province only, client calls,
 * and the settings-screen texts.
 */

import { render, screen, waitFor } from '@testing-library/react-native';
import { act, type ReactElement } from 'react';
import { Text } from 'react-native';

import { getHealth, registerPushToken, updateUserSettings } from '@/api/client';
import type { UserResponse } from '@/api/types';
import SettingsScreen from '@/app/settings';
import { resetNotificationsForTests } from '@/lib/notifications';
import { checkServerPush, getPushToken, type PushDeps, type PushEnv } from '@/lib/push';
import { DEFAULT_SETTINGS, parseSettings, type Settings } from '@/lib/settings';
import { SettingsProvider, useSettings } from '@/lib/SettingsContext';
import { syncLocalNotifications } from '@/lib/useLocalNotifications';

import { mkHours } from './fixtures';
import { DEVICE, MemoryStorage } from './helpers';

jest.mock('@/api/client', () => {
  const actual = jest.requireActual('@/api/client');
  return { ...actual, createUser: jest.fn(), updateUserSettings: jest.fn(), deleteUser: jest.fn() };
});
const mockUpdate = updateUserSettings as jest.MockedFunction<typeof updateUserSettings>;
const N = jest.requireMock('expo-notifications');

const TOKEN = 'ExponentPushToken[abcdefghijklmnopqrstuv]';
const BUILD: PushEnv = {
  os: 'android',
  isDevice: true,
  executionEnvironment: 'standalone',
  projectId: 'eas-project-id',
};
const READY: Settings = {
  ...DEFAULT_SETTINGS,
  serverConsent: true,
  skinType: 'III',
  province: 'ปทุมธานี',
  notifyEnabled: true,
  userId: 7,
  deviceId: DEVICE,
  serverPending: false,
};
const USER: UserResponse = {
  id: 7,
  skin_type: 'III',
  province: 'ปทุมธานี',
  notify_enabled: true,
  alert_threshold: 8,
  safe_threshold: 6,
  alert_burn_minutes: 30,
  updated_at: '2026-10-01T06:00:00+00:00',
  disclaimer: 'd',
};

function deps(over: Partial<PushDeps> = {}): PushDeps & {
  getToken: jest.Mock;
  register: jest.Mock;
  health: jest.Mock;
} {
  return {
    getToken: jest.fn(async () => TOKEN),
    register: jest.fn(async () => ({ registered: true, platform: 'android', active: true })),
    health: jest.fn(async () => ({ status: 'ok', push_scheduler: true })),
    platform: 'android',
    ...over,
  } as never;
}

function tokenApi(granted = true, data: unknown = TOKEN) {
  return {
    getPermissionsAsync: jest.fn(async () => ({ granted })),
    getExpoPushTokenAsync: jest.fn(async () => ({ data, type: 'expo' })),
  } as never as Parameters<typeof getPushToken>[1] & {
    getPermissionsAsync: jest.Mock;
    getExpoPushTokenAsync: jest.Mock;
  };
}

beforeEach(() => {
  mockUpdate.mockReset();
  mockUpdate.mockResolvedValue(USER);
  resetNotificationsForTests();
});

// --- 1-7: getPushToken ----------------------------------------------------------------------

describe('getPushToken', () => {
  it.each([
    ['1 web', { ...BUILD, os: 'web' }],
    ['2 simulator', { ...BUILD, isDevice: false }],
    ['3 Expo Go on Android', { ...BUILD, executionEnvironment: 'storeClient' }],
    ['4 no EAS project id', { ...BUILD, projectId: null }],
  ])('%s -> null, the token API is never called', async (_name, env) => {
    const api = tokenApi();
    expect(await getPushToken(env as PushEnv, api)).toBeNull();
    expect(api.getExpoPushTokenAsync).not.toHaveBeenCalled();
  });

  it('5 no notification permission -> null (never asks itself)', async () => {
    const api = tokenApi(false);
    expect(await getPushToken(BUILD, api)).toBeNull();
    expect(api.getExpoPushTokenAsync).not.toHaveBeenCalled();
  });

  it('6 the token call throws -> null, not an exception', async () => {
    const api = tokenApi();
    api.getExpoPushTokenAsync.mockRejectedValue(new Error('FCM not configured'));
    await expect(getPushToken(BUILD, api)).resolves.toBeNull();
    const bad = tokenApi(true, 'not-a-token');
    expect(await getPushToken(BUILD, bad)).toBeNull();
  });

  it('7 a build with everything set -> the token, with the project id', async () => {
    const api = tokenApi();
    expect(await getPushToken(BUILD, api)).toBe(TOKEN);
    expect(api.getExpoPushTokenAsync).toHaveBeenCalledWith({ projectId: 'eas-project-id' });
    // no notifications module (Expo Go Android wrapper result) -> null
    resetNotificationsForTests({ mod: null, reason: 'load-failed' });
    expect(await getPushToken(BUILD)).toBeNull();
  });
});

// --- 8-16: checkServerPush (conditions a-e) -------------------------------------------------

describe('checkServerPush', () => {
  it('8 all conditions met -> true, token registered for this user and device', async () => {
    const d = deps();
    expect(await checkServerPush(READY, d)).toBe(true);
    expect(d.register).toHaveBeenCalledWith(7, DEVICE, TOKEN, 'android');
  });

  it.each([
    ['9 no consent', { serverConsent: false }],
    ['10 no province', { province: null }],
    ['11 alerts off', { notifyEnabled: false }],
    ['12 last sync failed', { serverPending: true }],
    ['no server user yet', { userId: null }],
    ['no skin type', { skinType: null }],
  ])('%s -> false and nothing is sent', async (_n, patch) => {
    const d = deps();
    expect(await checkServerPush({ ...READY, ...patch } as Settings, d)).toBe(false);
    expect(d.getToken).not.toHaveBeenCalled();
    expect(d.register).not.toHaveBeenCalled();
    expect(d.health).not.toHaveBeenCalled();
  });

  it('13 no token -> false, nothing registered', async () => {
    const d = deps({ getToken: jest.fn(async () => null) });
    expect(await checkServerPush(READY, d)).toBe(false);
    expect(d.register).not.toHaveBeenCalled();
  });

  it.each([
    ['403', Object.assign(new Error('forbidden'), { status: 403 })],
    ['422', Object.assign(new Error('bad token'), { status: 422 })],
    ['network error', new TypeError('Network request failed')],
  ])('14 register fails (%s) -> false', async (_n, err) => {
    const d = deps({ register: jest.fn().mockRejectedValue(err) });
    expect(await checkServerPush(READY, d)).toBe(false);
    expect(d.health).not.toHaveBeenCalled();
  });

  it('15 /health says push_scheduler false (or missing) -> false', async () => {
    expect(await checkServerPush(READY, deps({ health: jest.fn(async () => ({ push_scheduler: false })) }))).toBe(false);
    expect(await checkServerPush(READY, deps({ health: jest.fn(async () => ({ status: 'ok' })) }))).toBe(false);
  });

  it('16 /health fails -> false', async () => {
    const d = deps({ health: jest.fn().mockRejectedValue(new TypeError('Network request failed')) });
    expect(await checkServerPush(READY, d)).toBe(false);
  });
});

// --- 17, 21, 22, 12: the provider -----------------------------------------------------------

function Probe() {
  const { pushActive, settings } = useSettings();
  return (
    <Text testID="probe">
      {pushActive ? 'push' : 'local'}|{settings.serverPending ? 'pending' : 'synced'}
    </Text>
  );
}

function renderProvider(ui: ReactElement, storage: MemoryStorage, d: PushDeps) {
  return render(
    <SettingsProvider storage={storage} newDeviceId={() => DEVICE} pushDeps={d}>
      {ui}
    </SettingsProvider>,
  );
}

describe('SettingsProvider pushActive', () => {
  it('17 starts false on every app start (never read from storage), then becomes true', async () => {
    let release!: (t: string) => void;
    const d = deps({ getToken: jest.fn(() => new Promise<string>((r) => (release = r))) });
    const storage = new MemoryStorage({ ...READY, pushActive: true } as Partial<Settings>);
    await renderProvider(<Probe />, storage, d);
    await waitFor(() => expect(d.getToken).toHaveBeenCalled());
    expect(screen.getByTestId('probe')).toHaveTextContent('local|synced');
    await act(async () => release(TOKEN));
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('push|synced'));
    // a stored "pushActive" is ignored when loading, and the app never stores it
    expect(parseSettings(JSON.stringify({ pushActive: true }))).not.toHaveProperty('pushActive');
  });

  it('12 a failed sync is remembered and retried on start; push waits while it fails', async () => {
    mockUpdate.mockRejectedValueOnce(new TypeError('Network request failed'));
    const storage = new MemoryStorage({ ...READY, serverPending: true });
    const d = deps();
    await renderProvider(<Probe />, storage, d);
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledTimes(1)); // retried on open
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('local|pending'));
    expect(d.register).not.toHaveBeenCalled();
    expect(storage.stored()?.serverPending).toBe(true);
  });

  it('12 next start with a working server: the retry clears serverPending, then push is on', async () => {
    // one render per test: a second render in the same test broke `screen` for later tests
    const storage = new MemoryStorage({ ...READY, serverPending: true });
    const d = deps();
    await renderProvider(<Probe />, storage, d);
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('push|synced'));
    expect(mockUpdate).toHaveBeenCalledTimes(1);
    expect(storage.stored()?.serverPending).toBe(false);
    expect(d.register).toHaveBeenCalledWith(7, DEVICE, TOKEN, 'android');
  });

  it('21 GPS mode sends only the province name, never coordinates', async () => {
    const storage = new MemoryStorage({ ...READY, locationMode: 'gps', province: null });
    let api!: ReturnType<typeof useSettings>;
    function Grab() {
      api = useSettings();
      return null;
    }
    await renderProvider(<Grab />, storage, deps());
    await act(async () => api.update({ province: 'นนทบุรี' }));
    await waitFor(() => expect(mockUpdate).toHaveBeenCalled());
    const body = mockUpdate.mock.calls[mockUpdate.mock.calls.length - 1][2];
    expect(body).toEqual({
      skin_type: 'III',
      notify_enabled: true,
      alert_threshold: 8,
      alert_burn_minutes: 30,
      province: 'นนทบุรี',
    });
    expect(JSON.stringify(body)).not.toMatch(/lat|lon|14\.0|100\.5/);
  });

  it('22 withdrawing consent turns push off (back to local alerts), token never re-sent', async () => {
    const { deleteUser } = jest.requireMock('@/api/client');
    deleteUser.mockResolvedValue(undefined);
    const storage = new MemoryStorage(READY);
    const d = deps();
    let api!: ReturnType<typeof useSettings>;
    function Grab() {
      api = useSettings();
      return <Probe />;
    }
    await renderProvider(<Grab />, storage, d);
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent(/^push\|/));
    const registered = d.register.mock.calls.length;
    await act(async () => api.update({ serverConsent: false }));
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent(/^local\|/));
    expect(d.register.mock.calls.length).toBe(registered);
  });
});

// --- 18-20: no double alerts ----------------------------------------------------------------

describe('local notifications while server push is active', () => {
  const at = (iso: string) => Date.parse(iso);
  const NOW = at('2026-09-29T05:30:00+07:00');
  const HOURS = mkHours('2026-09-29T05:00:00+07:00', [
    0, 0.6, 2, 4, 6, 7.5, 9, 10, 10.2, 9.5, 7, 5.9, 4, 2, 0.8, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  ]);
  const s: Settings = {
    ...READY,
    sunStartedAt: at('2026-09-29T10:00:00+07:00'),
    reapplyAt: at('2026-09-29T12:00:00+07:00'),
  };
  const kinds = async () =>
    (await N.getAllScheduledNotificationsAsync()).map(
      (n: { content: { data: { kind: string } } }) => n.content.data.kind,
    );

  beforeEach(() => N.__reset());

  it('18 pushActive: no local "UV สูง"/"ปลอดภัยแล้ว", daily/burn/reapply stay local', async () => {
    await syncLocalNotifications(HOURS, s, at('2026-09-29T10:05:00+07:00'), true);
    const k = await kinds();
    expect(k).not.toContain('uv_high');
    expect(k).not.toContain('uv_safe');
    expect(k).toEqual(expect.arrayContaining(['burn', 'reapply']));
    expect(k.some((x: string) => x.startsWith('daily'))).toBe(true);
  });

  it('19 push turned off again: the next run schedules the UV alerts locally', async () => {
    await syncLocalNotifications(HOURS, s, NOW, true);
    expect(await kinds()).not.toContain('uv_high');
    await syncLocalNotifications(HOURS, s, NOW, false);
    const k = await kinds();
    expect(k).toContain('uv_high');
    expect(k).toContain('uv_safe');
  });

  it('20 pushActive false is exactly day 22 (default argument)', async () => {
    await syncLocalNotifications(HOURS, s, NOW);
    const a = (await kinds()).sort();
    N.__reset();
    await syncLocalNotifications(HOURS, s, NOW, false);
    expect((await kinds()).sort()).toEqual(a);
    expect(a).toContain('uv_high');
  });
});

// --- 23-24: client ----------------------------------------------------------------------------

describe('client', () => {
  const ok = (body: unknown) =>
    jest.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(body) });

  it('23 registerPushToken: PUT /users/{id}/push-token with X-Device-Id and {token, platform}', async () => {
    const f = ok({ registered: true, platform: 'android', active: true });
    const r = await registerPushToken(7, DEVICE, TOKEN, 'android', {
      baseUrl: 'http://api.test',
      fetchImpl: f as unknown as typeof fetch,
    });
    expect(r.registered).toBe(true);
    const [url, init] = f.mock.calls[0];
    expect(url).toBe('http://api.test/users/7/push-token');
    expect(init.method).toBe('PUT');
    expect(init.headers['X-Device-Id']).toBe(DEVICE);
    expect(JSON.parse(init.body)).toEqual({ token: TOKEN, platform: 'android' });
    expect(init.body).not.toContain(DEVICE);
  });

  it('24 getHealth reads push_scheduler', async () => {
    const f = ok({ status: 'ok', push_scheduler: true });
    const h = await getHealth({ baseUrl: 'http://api.test', fetchImpl: f as unknown as typeof fetch });
    expect(f.mock.calls[0][0]).toBe('http://api.test/health');
    expect(h.push_scheduler).toBe(true);
  });
});

// --- 25-27: settings screen -------------------------------------------------------------------

describe('settings screen', () => {
  async function open(st: Partial<Settings>, d: PushDeps) {
    await renderProvider(<SettingsScreen />, new MemoryStorage(st), d);
    await screen.findByTestId('settings-skin', {}, { timeout: 5000 });
  }

  it('25 consent but no province yet: says server push is not working yet', async () => {
    await open({ ...READY, province: null }, deps());
    expect(screen.getByTestId('push-no-province')).toHaveTextContent(/ยังไม่รู้จังหวัด/);
    expect(screen.queryByTestId('push-status')).toBeNull();
  });

  it('26 "ข้อมูลของฉัน" says the province (not GPS) and the push token are stored', async () => {
    await open({ skinType: 'III' }, deps());
    expect(screen.getByTestId('my-data-text')).toHaveTextContent(/จังหวัด/);
    expect(screen.getByTestId('my-data-text')).toHaveTextContent(/ไม่เก็บพิกัด GPS/);
    expect(screen.getByTestId('my-data-text')).toHaveTextContent(/push token/);
  });

  it('27 push active: says so, and that no push arrives if the server stops', async () => {
    await open(READY, deps());
    expect(await screen.findByTestId('push-status')).toHaveTextContent(/จ\.ปทุมธานี/);
    expect(screen.getByTestId('push-status')).toHaveTextContent(/ถ้าเซิร์ฟเวอร์ปิดหลังจากนั้น/);
    expect(screen.getByTestId('notify-limits')).toHaveTextContent(/ถ้าเซิร์ฟเวอร์ปิด push จะไม่มา/);
  });
});
