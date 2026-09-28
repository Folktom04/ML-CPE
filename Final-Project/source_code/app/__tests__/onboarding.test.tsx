import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import * as Location from 'expo-location';
import { useRouter } from 'expo-router';

import { createUser, updateUserSettings } from '@/api/client';
import OnboardingScreen from '@/app/onboarding';
import ProvinceScreen from '@/app/province';

import { MemoryStorage, renderWithSettings } from './helpers';

jest.mock('@/api/client', () => {
  const actual = jest.requireActual('@/api/client');
  return { ...actual, createUser: jest.fn(), updateUserSettings: jest.fn() };
});

const router = useRouter();
const L = jest.mocked(Location);

beforeEach(() => {
  jest.clearAllMocks();
  L.requestForegroundPermissionsAsync.mockResolvedValue({ status: 'granted' } as never);
});

async function toLocationStep() {
  expect(screen.getByTestId('onboarding-step')).toHaveTextContent(/ขั้นที่ 1 จาก 4/);
  await fireEvent.press(screen.getByTestId('onboarding-start'));
  expect(screen.getByTestId('onboarding-step')).toHaveTextContent(/ขั้นที่ 2 จาก 4 · ตำแหน่ง/);
}

it('install -> allow location -> skin quiz -> consent -> home, nothing sent without consent', async () => {
  const storage = new MemoryStorage();
  await renderWithSettings(<OnboardingScreen />, storage);
  await toLocationStep();
  expect(screen.getByTestId('location-next')).toBeDisabled();
  await fireEvent.press(screen.getByTestId('use-gps'));
  await waitFor(() =>
    expect(screen.getByTestId('onboarding-step')).toHaveTextContent(/ประเภทผิว/),
  );
  expect(L.requestForegroundPermissionsAsync).toHaveBeenCalledTimes(1);
  expect(storage.stored()?.locationMode).toBe('gps');

  await fireEvent.press(screen.getByTestId('open-quiz'));
  expect(router.push).toHaveBeenCalledWith('/quiz');
  await fireEvent.press(screen.getByTestId('skin-skip'));
  expect(screen.getByTestId('onboarding-step')).toHaveTextContent(/ความยินยอม/);
  expect(screen.getByText(/ยินยอมให้ส่งประเภทผิว จังหวัด และการตั้งค่าการแจ้งเตือน/)).toBeTruthy();
  expect(screen.getByText(/ส่งแค่ชื่อจังหวัด ไม่ส่งพิกัด GPS/)).toBeTruthy();
  expect(screen.getByTestId('consent-switch').props.value).toBe(false);

  await fireEvent.press(screen.getByTestId('onboarding-finish'));
  await waitFor(() => expect(storage.stored()?.onboarded).toBe(true));
  expect(router.replace).toHaveBeenCalledWith('/');
  expect(createUser).not.toHaveBeenCalled();
  expect(updateUserSettings).not.toHaveBeenCalled();
});

it('location denied -> province picker -> the chosen province is used', async () => {
  L.requestForegroundPermissionsAsync.mockResolvedValue({ status: 'denied' } as never);
  const storage = new MemoryStorage();
  // both screens share one SettingsProvider, as in the app's navigation stack
  await renderWithSettings(
    <>
      <OnboardingScreen />
      <ProvinceScreen />
    </>,
    storage,
  );
  await toLocationStep();
  await fireEvent.press(screen.getByTestId('use-gps'));
  expect(await screen.findByTestId('location-denied')).toHaveTextContent(/เลือกจังหวัดแทน/);
  expect(router.push).toHaveBeenCalledWith('/province');
  expect(storage.stored()?.locationMode ?? null).toBeNull();

  await fireEvent.changeText(screen.getByTestId('province-search'), 'chiang mai');
  await fireEvent.press(screen.getByTestId('province-Chiang Mai'));
  await waitFor(() =>
    expect(storage.stored()).toMatchObject({ locationMode: 'province', province: 'เชียงใหม่' }),
  );
  expect(router.back).toHaveBeenCalled();
  expect(screen.getByTestId('chosen-province')).toHaveTextContent('จ.เชียงใหม่ (เลือกเอง)');
  expect(screen.getByTestId('location-next')).not.toBeDisabled();
  await fireEvent.press(screen.getByTestId('location-next'));
  expect(screen.getByTestId('onboarding-step')).toHaveTextContent(/ประเภทผิว/);
});

it('a skin type chosen in the quiz lets the user continue, and Back works', async () => {
  const storage = new MemoryStorage({ skinType: 'IV', locationMode: 'gps' });
  await renderWithSettings(<OnboardingScreen />, storage);
  await fireEvent.press(await screen.findByTestId('onboarding-start'));
  await fireEvent.press(screen.getByTestId('location-next'));
  expect(screen.getByTestId('chosen-skin')).toHaveTextContent(/ผิวประเภท IV/);
  await fireEvent.press(screen.getByTestId('back'));
  expect(screen.getByTestId('onboarding-step')).toHaveTextContent(/ตำแหน่ง/);
  expect(screen.getByTestId('chosen-gps')).toBeTruthy();
});

it('province search shows a message when nothing matches', async () => {
  await renderWithSettings(<ProvinceScreen />);
  await fireEvent.changeText(screen.getByTestId('province-search'), 'zzz');
  expect(screen.getByText('ไม่พบจังหวัดที่ค้นหา')).toBeTruthy();
});
