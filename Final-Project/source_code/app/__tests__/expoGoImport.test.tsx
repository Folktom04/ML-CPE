/**
 * Regression test for the Expo Go Android crash (expo-notifications 57.0.21): the package throws
 * as soon as it is imported ("…removed from Expo Go with the release of SDK 53"), which used to
 * take down `_layout` and so every route. In this file the package throws for EVERY test (a
 * hoisted jest.mock replaces the fake from jest.setup.ts), so nothing can leak into other files.
 * Every route and the settings provider must still import, and the app must still render.
 */

import { render, screen } from '@testing-library/react-native';

jest.mock('expo-notifications', () => {
  throw new Error(
    'expo-notifications: Android Push notifications (remote notifications) functionality ' +
      'provided by expo-notifications was removed from Expo Go with the release of SDK 53.',
  );
});

const MODULES = [
  '@/app/_layout',
  '@/app/index',
  '@/app/settings',
  '@/app/onboarding',
  '@/app/quiz',
  '@/app/province',
  '@/app/camera',
  '@/app/light',
  '@/lib/SettingsContext',
  '@/lib/notifications',
  '@/lib/useLocalNotifications',
  '@/components/SunSessionCard',
];

it.each(MODULES)('%s imports although expo-notifications throws', (m) => {
  let mod: Record<string, unknown> | undefined;
  expect(() => {
    mod = require(m);
  }).not.toThrow();
  expect(mod).toBeTruthy();
});

it('every route keeps its default export (no "missing the required default export")', () => {
  for (const m of MODULES.filter((x) => x.startsWith('@/app/'))) {
    expect(typeof require(m).default).toBe('function');
  }
});

it('the settings screen renders and explains why there are no notifications', async () => {
  const n = require('@/lib/notifications');
  n.resetNotificationsForTests();
  // a development build on Android: the require is attempted, throws, and is caught
  expect(n.loadNotifications({ os: 'android', executionEnvironment: 'bare' }).reason).toBe(
    'load-failed',
  );
  const { SettingsProvider } = require('@/lib/SettingsContext');
  const SettingsScreen = require('@/app/settings').default;
  const { MemoryStorage } = require('./helpers');
  await render(
    <SettingsProvider storage={new MemoryStorage({ skinType: 'III' })}>
      <SettingsScreen />
    </SettingsProvider>,
  );
  expect(await screen.findByTestId('notify-unavailable')).toHaveTextContent(
    /โหลดระบบแจ้งเตือนของเครื่องไม่สำเร็จ/,
  );
  expect(screen.getByTestId('notify-switch').props.disabled).toBe(true);
});
