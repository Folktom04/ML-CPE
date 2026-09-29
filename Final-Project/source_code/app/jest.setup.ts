/* Jest setup (day 19): native modules and navigation are replaced by simple fakes. */

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

jest.mock('expo-crypto', () => ({
  randomUUID: jest.fn(() => '00000000-0000-4000-8000-00000000abcd'),
}));

jest.mock('expo-router', () => {
  const router = {
    push: jest.fn(),
    back: jest.fn(),
    replace: jest.fn(),
    canGoBack: jest.fn(() => true),
  };
  return {
    Link: ({ children }: { children: unknown }) => children,
    Redirect: jest.fn(() => null),
    useRouter: () => router,
  };
});

/*
 * Day 20: camera, sensors, image re-encoding and file deletion. Tests drive them through
 * jest.requireMock(...): e.g. `__emit(value)` on a sensor, `__setPermission(...)` on the camera.
 */
jest.mock('expo-sensors', () => {
  const sensor = () => {
    let listener: ((v: unknown) => void) | null = null;
    return {
      isAvailableAsync: jest.fn(async () => true),
      setUpdateInterval: jest.fn(),
      addListener: jest.fn((l: (v: unknown) => void) => {
        listener = l;
        return { remove: jest.fn(() => (listener = null)) };
      }),
      __emit: (v: unknown) => listener?.(v),
      __hasListener: () => listener !== null,
    };
  };
  return { LightSensor: sensor(), Accelerometer: sensor() };
});

jest.mock('expo-camera', () => {
  const React = require('react');
  const state: {
    permission: unknown;
    takePictureAsync: jest.Mock;
    requestPermission: jest.Mock;
  } = {
    permission: { granted: true, canAskAgain: true, status: 'granted' } as unknown,
    takePictureAsync: jest.fn(async (_opts?: unknown) => ({
      uri: 'file:///cache/Camera/original.jpg',
      width: 3000,
      height: 4000,
    })),
    requestPermission: jest.fn(async () => state.permission),
  };
  const CameraView = React.forwardRef((_props: unknown, ref: unknown) => {
    React.useImperativeHandle(ref, () => ({ takePictureAsync: state.takePictureAsync }));
    return null;
  });
  return {
    CameraView,
    useCameraPermissions: () => [state.permission, state.requestPermission],
    __state: state,
  };
});

jest.mock('expo-image-manipulator', () => {
  const ctx: { resize: jest.Mock; renderAsync: jest.Mock } = {
    resize: jest.fn(() => ctx),
    renderAsync: jest.fn(async () => ({
      saveAsync: jest.fn(async () => ({ uri: 'file:///cache/ImageManipulator/clean.jpg' })),
    })),
  };
  return {
    ImageManipulator: { manipulate: jest.fn(() => ctx) },
    SaveFormat: { JPEG: 'jpeg', PNG: 'png' },
    __ctx: ctx,
  };
});

// File implements Blob like expo-file-system's (bytes/name/type): expo/fetch reads it via bytes().
jest.mock('expo-file-system', () => {
  const deleted: string[] = [];
  class File {
    uri: string;
    exists = true;
    constructor(uri: string) {
      this.uri = uri;
    }
    get name() {
      return this.uri.split('/').pop() ?? '';
    }
    get type() {
      return /\.jpe?g$/i.test(this.uri) ? 'image/jpeg' : '';
    }
    async bytes() {
      return new Uint8Array([0xff, 0xd8, 0xff, 0xd9]); // tiny JPEG markers
    }
    delete() {
      deleted.push(this.uri);
    }
  }
  return { File, __deleted: deleted };
});

// expo-location (day 21): permission granted and a fix in Pathum Thani unless a test overrides it.
jest.mock('expo-location', () => ({
  Accuracy: { Balanced: 3 },
  requestForegroundPermissionsAsync: jest.fn(async () => ({ status: 'granted' })),
  getForegroundPermissionsAsync: jest.fn(async () => ({ status: 'granted' })),
  getLastKnownPositionAsync: jest.fn(async () => null),
  getCurrentPositionAsync: jest.fn(async () => ({
    coords: { latitude: 14.02083, longitude: 100.52504 },
  })),
}));

// expo-notifications (day 22): an in-memory schedule; permission granted unless a test overrides.
jest.mock('expo-notifications', () => {
  type MockReq = { content: { data?: { kind?: string } }; trigger: unknown };
  let scheduled: ({ identifier: string } & MockReq)[] = [];
  let n = 0;
  return {
    AndroidImportance: { HIGH: 4, DEFAULT: 3 },
    SchedulableTriggerInputTypes: { DATE: 'date' },
    setNotificationHandler: jest.fn(),
    setNotificationChannelAsync: jest.fn(async () => null),
    getPermissionsAsync: jest.fn(async () => ({ granted: true, canAskAgain: true })),
    requestPermissionsAsync: jest.fn(async () => ({ granted: true })),
    scheduleNotificationAsync: jest.fn(async (req: MockReq) => {
      n += 1;
      scheduled.push({ identifier: `n${n}`, ...req });
      return `n${n}`;
    }),
    getAllScheduledNotificationsAsync: jest.fn(async () => scheduled.slice()),
    cancelScheduledNotificationAsync: jest.fn(async (id: string) => {
      scheduled = scheduled.filter((s) => s.identifier !== id);
    }),
    cancelAllScheduledNotificationsAsync: jest.fn(async () => {
      scheduled = [];
    }),
    __reset: () => {
      scheduled = [];
      n = 0;
    },
  };
});
