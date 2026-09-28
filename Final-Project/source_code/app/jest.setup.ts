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

jest.mock('expo-file-system', () => {
  const deleted: string[] = [];
  class File {
    uri: string;
    exists = true;
    constructor(uri: string) {
      this.uri = uri;
    }
    delete() {
      deleted.push(this.uri);
    }
  }
  return { File, __deleted: deleted };
});
