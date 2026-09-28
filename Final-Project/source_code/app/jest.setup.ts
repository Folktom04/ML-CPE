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
