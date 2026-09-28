/**
 * Settings provider (day 19): loads settings from the phone, saves every change locally first,
 * then, only with the user's explicit consent (`serverConsent`), syncs the server fields (skin
 * type, alerts) with POST/PUT /users. Withdrawing consent deletes the server record. The app
 * keeps working when the server is unreachable; the sync state says "not synced yet".
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import { ApiError, createUser, deleteUser, describeError, updateUserSettings } from '@/api/client';
import { clearAllNotifications } from '@/lib/notifications';
import {
  clearSettings,
  DEFAULT_SETTINGS,
  loadSettings,
  saveSettings,
  serverSettings,
  type KeyValueStorage,
  type Settings,
} from '@/lib/settings';

export type SyncState =
  | { kind: 'idle' }
  | { kind: 'syncing' }
  | { kind: 'ok' }
  | { kind: 'error'; message: string };

type SettingsContextValue = {
  settings: Settings;
  /** false until the stored settings have been read. */
  ready: boolean;
  sync: SyncState;
  /** Save a change on the phone, then (with consent) sync it when a server field changed. */
  update: (patch: Partial<Settings>) => Promise<void>;
  /** Delete the server record (if any), then everything stored on the phone. */
  deleteMyData: () => Promise<void>;
};

const SERVER_KEYS: (keyof Settings)[] = [
  'serverConsent',
  'skinType',
  'notifyEnabled',
  'alertThreshold',
  'alertBurnMinutes',
  'province',
];

const SettingsContext = createContext<SettingsContextValue | null>(null);

/** Push the server fields: register when there is no user id yet (or it was lost). */
async function syncToServer(s: Settings): Promise<number> {
  const body = serverSettings(s);
  if (!s.skinType || !s.deviceId) throw new Error('skin type or device id missing');
  const register = () => createUser(s.deviceId!, { ...body, skin_type: s.skinType! });
  if (s.userId === null) return (await register()).id;
  try {
    return (await updateUserSettings(s.userId, s.deviceId, body)).id;
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return (await register()).id;
    throw err;
  }
}

export function SettingsProvider({
  children,
  storage = AsyncStorage,
  newDeviceId = Crypto.randomUUID,
}: {
  children: ReactNode;
  storage?: KeyValueStorage;
  newDeviceId?: () => string;
}) {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [ready, setReady] = useState(false);
  const [sync, setSync] = useState<SyncState>({ kind: 'idle' });
  const current = useRef<Settings>(DEFAULT_SETTINGS);

  const commit = useCallback(
    async (s: Settings) => {
      current.current = s;
      setSettings(s);
      await saveSettings(storage, s);
    },
    [storage],
  );

  useEffect(() => {
    let active = true;
    loadSettings(storage).then((s) => {
      if (!active) return;
      current.current = s;
      setSettings(s);
      setReady(true);
    });
    return () => {
      active = false;
    };
  }, [storage]);

  /** Consent withdrawn: delete the server record; if that fails, consent stays on. */
  const withdraw = useCallback(async () => {
    const { userId, deviceId } = current.current;
    if (userId === null || !deviceId) return;
    setSync({ kind: 'syncing' });
    try {
      await deleteUser(userId, deviceId);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) {
        await commit({ ...current.current, serverConsent: true });
        setSync({
          kind: 'error',
          message: `ยังลบข้อมูลบนเซิร์ฟเวอร์ไม่ได้ (${err instanceof ApiError ? err.message : describeError(err)})`,
        });
        return;
      }
    }
    await commit({ ...current.current, userId: null });
    setSync({ kind: 'idle' });
  }, [commit]);

  const update = useCallback(
    async (patch: Partial<Settings>) => {
      let next: Settings = { ...current.current, ...patch };
      if (!next.deviceId) next = { ...next, deviceId: newDeviceId() };
      await commit(next);
      if (patch.serverConsent === false) {
        await withdraw();
        return;
      }
      const serverChanged = SERVER_KEYS.some((k) => k in patch) || next.userId === null;
      if (!next.serverConsent || !next.skinType || !serverChanged) return;
      setSync({ kind: 'syncing' });
      try {
        const userId = await syncToServer(next);
        if (userId !== current.current.userId) await commit({ ...current.current, userId });
        setSync({ kind: 'ok' });
      } catch (err) {
        setSync({
          kind: 'error',
          message: err instanceof ApiError ? err.message : describeError(err),
        });
      }
    },
    [commit, newDeviceId, withdraw],
  );

  const deleteMyData = useCallback(async () => {
    const { userId, deviceId } = current.current;
    if (userId !== null && deviceId) {
      try {
        await deleteUser(userId, deviceId);
      } catch (err) {
        // already gone on the server: still clear the phone. Anything else: keep local data so
        // the user can retry (otherwise the server record could never be deleted).
        if (!(err instanceof ApiError && err.status === 404)) throw err;
      }
    }
    await clearSettings(storage);
    await clearAllNotifications();
    current.current = { ...DEFAULT_SETTINGS };
    setSettings(current.current);
    setSync({ kind: 'idle' });
  }, [storage]);

  const value = useMemo(
    () => ({ settings, ready, sync, update, deleteMyData }),
    [settings, ready, sync, update, deleteMyData],
  );
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used inside <SettingsProvider>');
  return ctx;
}
