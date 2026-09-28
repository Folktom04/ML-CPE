import { act, render, screen, waitFor } from '@testing-library/react-native';
import { Platform } from 'react-native';

import LightScreen from '@/app/light';

const { LightSensor, Accelerometer } = jest.requireMock('expo-sensors');

function onPlatform(os: string) {
  jest.replaceProperty(Platform, 'OS', os as typeof Platform.OS);
}

beforeEach(() => {
  LightSensor.isAvailableAsync.mockResolvedValue(true);
  LightSensor.addListener.mockClear();
});

afterEach(() => jest.restoreAllMocks());

it('iOS: light sensor is hidden, with an Android-only message', async () => {
  onPlatform('ios');
  await render(<LightScreen />);
  expect(screen.getByTestId('light-android-only')).toHaveTextContent('ใช้ได้เฉพาะ Android', {
    exact: false,
  });
  expect(LightSensor.addListener).not.toHaveBeenCalled();
});

it('Android without a light sensor says so', async () => {
  onPlatform('android');
  LightSensor.isAvailableAsync.mockResolvedValue(false);
  await render(<LightScreen />);
  expect(await screen.findByTestId('light-unavailable')).toBeTruthy();
});

it('Android: median lux, orientation check and the uncalibrated note', async () => {
  onPlatform('android');
  await render(<LightScreen />);
  await waitFor(() => expect(LightSensor.__hasListener()).toBe(true));
  await waitFor(() => expect(Accelerometer.__hasListener()).toBe(true));
  expect(screen.getByTestId('lux-uncalibrated')).toHaveTextContent('ไม่เปลี่ยนค่า UVI', {
    exact: false,
  });

  await act(async () => {
    for (const lux of [1000, 1200, 90000]) LightSensor.__emit({ illuminance: lux });
  });
  expect(screen.getByTestId('lux-value')).toHaveTextContent('1,200 lux', {
    exact: false,
  }); // spike ignored

  await act(async () => Accelerometer.__emit({ x: 0, y: 0, z: 1 })); // Android: face up
  expect(screen.getByTestId('orientation-status')).toHaveTextContent('ทิศทางถูกต้อง', {
    exact: false,
  });
  expect(screen.queryByTestId('lux-not-usable')).toBeNull();

  await act(async () => Accelerometer.__emit({ x: 0, y: 0.5, z: 0.866 })); // 30° tilt
  expect(screen.getByTestId('orientation-status')).toHaveTextContent('เอียงเกินไป (เอียง 30°)', {
    exact: false,
  });
  expect(screen.getByTestId('lux-not-usable')).toBeTruthy();

  await act(async () => Accelerometer.__emit({ x: 0, y: 0, z: -1 })); // face down
  expect(screen.getByTestId('orientation-status')).toHaveTextContent('ต้องหงายขึ้นฟ้า', {
    exact: false,
  });
});

it('stops listening when the screen closes', async () => {
  onPlatform('android');
  const view = await render(<LightScreen />);
  await waitFor(() => expect(LightSensor.__hasListener()).toBe(true));
  await act(async () => view.unmount());
  expect(LightSensor.__hasListener()).toBe(false);
  expect(Accelerometer.__hasListener()).toBe(false);
});
