import { act, fireEvent, screen, waitFor } from '@testing-library/react-native';

import { ApiError, uploadSkyImage } from '@/api/client';
import CameraScreen from '@/app/camera';
import { SKY_DOMAIN_GAP_TH, SKY_NOTICE_TH } from '@/lib/sky';

import { sampleSky, unsureSky } from './fixtures_sky';
import { MemoryStorage, renderWithSettings } from './helpers';

jest.mock('@/api/client', () => {
  const actual = jest.requireActual('@/api/client');
  return { ...actual, uploadSkyImage: jest.fn() };
});
const mockUpload = uploadSkyImage as jest.MockedFunction<typeof uploadSkyImage>;
const cam = jest.requireMock('expo-camera').__state;
const fs = jest.requireMock('expo-file-system');
const accel = jest.requireMock('expo-sensors').Accelerometer;

const ORIGINAL = 'file:///cache/Camera/original.jpg';
const CLEAN = 'file:///cache/ImageManipulator/clean.jpg';

beforeEach(() => {
  mockUpload.mockReset();
  cam.takePictureAsync.mockClear();
  cam.requestPermission.mockClear();
  cam.permission = { granted: true, canAskAgain: true, status: 'granted' };
  fs.__deleted.length = 0;
});

const acked = () => new MemoryStorage({ skyNoticeAck: true });

it('shows the privacy notice before the first photo and remembers the answer', async () => {
  const storage = new MemoryStorage();
  await renderWithSettings(<CameraScreen />, storage);
  expect(await screen.findByTestId('sky-notice')).toHaveTextContent(SKY_NOTICE_TH, {
    exact: false,
  });
  expect(screen.queryByTestId('camera-shoot')).toBeNull();
  await act(async () => fireEvent.press(screen.getByTestId('sky-notice-ack')));
  expect(await screen.findByTestId('camera-shoot')).toBeTruthy();
  expect(storage.stored()?.skyNoticeAck).toBe(true);
});

it('does not show the notice again once acknowledged', async () => {
  await renderWithSettings(<CameraScreen />, acked());
  expect(await screen.findByTestId('camera-shoot')).toBeTruthy();
  expect(screen.queryByTestId('sky-notice')).toBeNull();
});

it('without camera permission: Thai message and a button to ask again', async () => {
  cam.permission = { granted: false, canAskAgain: true, status: 'denied' };
  await renderWithSettings(<CameraScreen />, acked());
  expect(await screen.findByTestId('camera-denied')).toHaveTextContent('ส่วนอื่นของแอปยังใช้ได้', {
    exact: false,
  });
  fireEvent.press(screen.getByTestId('camera-request'));
  expect(cam.requestPermission).toHaveBeenCalled();
});

it('permanently denied: points to the phone settings', async () => {
  cam.permission = { granted: false, canAskAgain: false, status: 'denied' };
  await renderWithSettings(<CameraScreen />, acked());
  expect(await screen.findByText(/การตั้งค่าของเครื่อง/)).toBeTruthy();
  expect(screen.queryByTestId('camera-request')).toBeNull();
});

it('takes a photo without EXIF, uploads the re-encoded copy, shows the result, deletes files', async () => {
  mockUpload.mockResolvedValue(sampleSky(0.87));
  await renderWithSettings(<CameraScreen />, acked());
  await act(async () => fireEvent.press(await screen.findByTestId('camera-shoot')));
  expect(await screen.findByTestId('sky-class')).toHaveTextContent('เมฆหนาสีขาว', { exact: false });
  expect(cam.takePictureAsync).toHaveBeenCalledWith({
    quality: 0.8,
    exif: false,
  });
  expect(mockUpload).toHaveBeenCalledWith(CLEAN); // never the original file
  expect(fs.__deleted).toEqual([ORIGINAL, CLEAN]);
  expect(screen.getByTestId('sky-confidence')).toHaveTextContent('87%', {
    exact: false,
  });
  expect(screen.getByTestId('sky-cloud')).toHaveTextContent('62%', {
    exact: false,
  });
  expect(screen.getByTestId('sky-supporting')).toHaveTextContent('ไม่เปลี่ยนค่า UVI', {
    exact: false,
  });
  expect(screen.getByTestId('sky-domain-gap')).toHaveTextContent(SKY_DOMAIN_GAP_TH, {
    exact: false,
  });
  expect(screen.queryByTestId('sky-unsure')).toBeNull();
});

it('confidence < 0.5: "ไม่แน่ใจ" with the top 2 classes and the domain-gap note', async () => {
  mockUpload.mockResolvedValue(unsureSky());
  await renderWithSettings(<CameraScreen />, acked());
  await act(async () => fireEvent.press(await screen.findByTestId('camera-shoot')));
  expect(await screen.findByTestId('sky-unsure')).toHaveTextContent('ไม่แน่ใจ', { exact: false });
  expect(screen.getByTestId('sky-top-1')).toHaveTextContent('1. เมฆบางคลุมทั่วฟ้า (41%)', {
    exact: false,
  });
  expect(screen.getByTestId('sky-top-2')).toHaveTextContent('2. เมฆบางสีขาว (33%)', {
    exact: false,
  });
  expect(screen.queryByTestId('sky-class')).toBeNull();
  expect(screen.getByTestId('sky-domain-gap')).toHaveTextContent(SKY_DOMAIN_GAP_TH, {
    exact: false,
  });
});

it('upload failure: Thai error, and both temporary files are still deleted', async () => {
  mockUpload.mockRejectedValue(
    new ApiError('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจอินเทอร์เน็ตหรือที่อยู่ API', {
      detail: 'TypeError: Network request failed',
    }),
  );
  await renderWithSettings(<CameraScreen />, acked());
  await act(async () => fireEvent.press(await screen.findByTestId('camera-shoot')));
  expect(await screen.findByTestId('camera-error')).toHaveTextContent(
    'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้',
    { exact: false },
  );
  expect(fs.__deleted).toEqual([ORIGINAL, CLEAN]);
});

it('asks to aim higher when the camera looks at the horizon', async () => {
  await renderWithSettings(<CameraScreen />, acked());
  await screen.findByTestId('camera-shoot');
  await waitFor(() => expect(accel.__hasListener()).toBe(true));
  await act(async () => accel.__emit({ x: 0, y: 1, z: 0 })); // upright: elevation 0°
  expect(screen.getByTestId('camera-aim-hint')).toHaveTextContent('ยกกล้องขึ้นอีก', {
    exact: false,
  });
  await act(async () => accel.__emit({ x: 0, y: 0, z: 1 })); // jest-expo is iOS: z=+1 → screen down
  expect(screen.queryByTestId('camera-aim-hint')).toBeNull();
});

it('shows the model cloud fraction (in the image, not the whole sky) only when the API sends it', async () => {
  mockUpload.mockResolvedValue({
    ...sampleSky(0.87),
    cloud_fraction_cnn: 0.55,
    reliability: { ...sampleSky().reliability, cloud_fraction_cnn: 'ผ่านเกณฑ์ ...' },
  });
  await renderWithSettings(<CameraScreen />, acked());
  await act(async () => fireEvent.press(await screen.findByTestId('camera-shoot')));
  expect(await screen.findByTestId('sky-cloud-cnn')).toHaveTextContent('55%', { exact: false });
  expect(screen.getByTestId('sky-cloud-cnn-note')).toHaveTextContent(
    'สัดส่วนเมฆในภาพ ไม่ใช่ทั้งท้องฟ้า',
  );
  expect(screen.getByText(/สัดส่วนเมฆ \(โมเดล\): ผ่านเกณฑ์/)).toBeTruthy();
  expect(screen.getByTestId('sky-supporting')).toHaveTextContent('ไม่เปลี่ยนค่า UVI', {
    exact: false,
  });
});

it('without cloud_fraction_cnn only the red/blue line is shown', async () => {
  mockUpload.mockResolvedValue(sampleSky(0.87));
  await renderWithSettings(<CameraScreen />, acked());
  await act(async () => fireEvent.press(await screen.findByTestId('camera-shoot')));
  expect(await screen.findByTestId('sky-cloud')).toBeTruthy();
  expect(screen.queryByTestId('sky-cloud-cnn')).toBeNull();
});
