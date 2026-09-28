import { fireEvent, screen, waitFor } from "@testing-library/react-native";

import {
  ApiError,
  createUser,
  deleteUser,
  updateUserSettings,
} from "@/api/client";
import type { UserResponse } from "@/api/types";
import SettingsScreen from "@/app/settings";

import { DEVICE, MemoryStorage, renderWithSettings } from "./helpers";

jest.mock("@/api/client", () => {
  const actual = jest.requireActual("@/api/client");
  return {
    ...actual,
    createUser: jest.fn(),
    updateUserSettings: jest.fn(),
    deleteUser: jest.fn(),
  };
});
const mockCreate = createUser as jest.MockedFunction<typeof createUser>;
const mockUpdate = updateUserSettings as jest.MockedFunction<
  typeof updateUserSettings
>;
const mockDelete = deleteUser as jest.MockedFunction<typeof deleteUser>;

function user(id: number): UserResponse {
  return {
    id,
    skin_type: "III",
    province: null,
    notify_enabled: true,
    alert_threshold: 8,
    safe_threshold: 6,
    alert_burn_minutes: 30,
    updated_at: "2026-09-28T06:00:00+00:00",
    disclaimer: "d",
  };
}

beforeEach(() => {
  mockCreate.mockReset();
  mockUpdate.mockReset();
  mockDelete.mockReset();
});

async function open(storage: MemoryStorage) {
  await renderWithSettings(<SettingsScreen />, storage);
  await screen.findByTestId("settings-skin", {}, { timeout: 5000 });
}

it('shows the stored settings and moves "safe again" with the alert level', async () => {
  const storage = new MemoryStorage({
    skinType: "III",
    userId: 7,
    deviceId: DEVICE,
    serverConsent: true,
  });
  mockUpdate.mockResolvedValue(user(7));
  await open(storage);
  expect(screen.getByTestId("settings-skin")).toHaveTextContent("ประเภท III");
  expect(screen.getByTestId("threshold-hint")).toHaveTextContent(
    /ตั้งแต่ 8 .*ต่ำกว่า 6/,
  );
  await fireEvent.press(screen.getByTestId("threshold-11"));
  expect(screen.getByTestId("threshold-hint")).toHaveTextContent(
    /ตั้งแต่ 11 .*ต่ำกว่า 9/,
  );
  await waitFor(() =>
    expect(screen.getByTestId("sync-state")).toHaveTextContent(
      /บนเซิร์ฟเวอร์แล้ว/,
    ),
  );
  expect(mockUpdate).toHaveBeenCalledWith(7, DEVICE, {
    skin_type: "III",
    notify_enabled: true,
    alert_threshold: 11,
    alert_burn_minutes: 30,
    province: null,
  });
  expect(storage.stored()).toMatchObject({ alertThreshold: 11, userId: 7 });
  await fireEvent.press(screen.getByTestId("threshold-6"));
  expect(screen.getByTestId("threshold-hint")).toHaveTextContent(
    /ตั้งแต่ 6 .*ต่ำกว่า 4/,
  );
});

it("sends nothing to the server without consent (the default)", async () => {
  const storage = new MemoryStorage({ skinType: "II" });
  await open(storage);
  expect(screen.getByTestId("sync-state")).toHaveTextContent(
    /เก็บในเครื่องเท่านั้น/,
  );
  await fireEvent.press(screen.getByTestId("threshold-11"));
  await fireEvent(screen.getByTestId("notify-switch"), "valueChange", false);
  await waitFor(() => expect(storage.stored()?.notifyEnabled).toBe(false));
  expect(storage.stored()?.alertThreshold).toBe(11);
  expect(screen.queryByTestId("burn-60")).toBeNull(); // 15/30/60 removed on day 22
  expect(mockCreate).not.toHaveBeenCalled();
  expect(mockUpdate).not.toHaveBeenCalled();
  expect(storage.stored()).toMatchObject({
    serverConsent: false,
    userId: null,
  });
});

it("registers when consent is given, with a new device id, and stores the user id", async () => {
  const storage = new MemoryStorage({ skinType: "II", alertBurnMinutes: 60 });
  mockCreate.mockResolvedValue(user(42));
  await open(storage);
  await fireEvent(screen.getByTestId("consent-switch"), "valueChange", true);
  await waitFor(() => expect(storage.stored()?.userId).toBe(42));
  expect(mockCreate).toHaveBeenCalledWith(DEVICE, {
    skin_type: "II",
    notify_enabled: true,
    alert_threshold: 8,
    alert_burn_minutes: 60,
    province: null,
  });
  expect(storage.stored()).toMatchObject({
    deviceId: DEVICE,
    alertBurnMinutes: 60,
  });
  expect(screen.queryByText(DEVICE)).toBeNull(); // the device id is never shown
});

it("local-only switches do not call the server once registered", async () => {
  const storage = new MemoryStorage({
    skinType: "II",
    userId: 3,
    deviceId: DEVICE,
    serverConsent: true,
  });
  await open(storage);
  await fireEvent(screen.getByTestId("daily-switch"), "valueChange", false);
  await waitFor(() => expect(storage.stored()?.dailySummary).toBe(false));
  expect(mockUpdate).not.toHaveBeenCalled();
  expect(mockCreate).not.toHaveBeenCalled();
});

it("keeps the change on the phone when the server is unreachable", async () => {
  const storage = new MemoryStorage({
    skinType: "III",
    userId: 7,
    deviceId: DEVICE,
    serverConsent: true,
  });
  mockUpdate.mockRejectedValue(new ApiError("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้"));
  await open(storage);
  await fireEvent(screen.getByTestId("notify-switch"), "valueChange", false);
  await waitFor(() =>
    expect(screen.getByTestId("sync-state")).toHaveTextContent(
      "บันทึกในเครื่องแล้ว แต่ยังไม่ได้ซิงก์กับเซิร์ฟเวอร์: เชื่อมต่อเซิร์ฟเวอร์ไม่ได้",
    ),
  );
  expect(storage.stored()?.notifyEnabled).toBe(false);
});

it("registers again when the server no longer knows the user (404)", async () => {
  const storage = new MemoryStorage({
    skinType: "III",
    userId: 7,
    deviceId: DEVICE,
    serverConsent: true,
  });
  mockUpdate.mockRejectedValue(new ApiError("ไม่พบ", { status: 404 }));
  mockCreate.mockResolvedValue(user(99));
  await open(storage);
  await fireEvent.press(screen.getByTestId("threshold-6"));
  await waitFor(() => expect(storage.stored()?.userId).toBe(99));
  expect(mockCreate).toHaveBeenCalledTimes(1);
});

it("deletes my data after confirmation: server first, then the phone", async () => {
  const storage = new MemoryStorage({
    skinType: "IV",
    userId: 7,
    deviceId: DEVICE,
    serverConsent: true,
  });
  mockDelete.mockResolvedValue(undefined);
  await open(storage);
  await fireEvent.press(screen.getByTestId("delete-start"));
  expect(screen.getByTestId("delete-confirm")).toHaveTextContent(
    /ย้อนกลับไม่ได้/,
  );
  expect(mockDelete).not.toHaveBeenCalled(); // nothing happens before confirming
  await fireEvent.press(screen.getByTestId("delete-cancel"));
  expect(screen.queryByTestId("delete-confirm")).toBeNull();
  await fireEvent.press(screen.getByTestId("delete-start"));
  await fireEvent.press(screen.getByTestId("delete-confirm-yes"));
  expect(await screen.findByTestId("deleted-note")).toBeTruthy();
  expect(mockDelete).toHaveBeenCalledWith(7, DEVICE);
  expect(storage.stored()).toBeNull();
  expect(screen.getByTestId("settings-skin")).toHaveTextContent(
    /ยังไม่ได้ระบุ/,
  );
});

it("keeps local data and shows an error when the server delete fails", async () => {
  const storage = new MemoryStorage({
    skinType: "IV",
    userId: 7,
    deviceId: DEVICE,
    serverConsent: true,
  });
  mockDelete.mockRejectedValue(new ApiError("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้"));
  await open(storage);
  await fireEvent.press(screen.getByTestId("delete-start"));
  await fireEvent.press(screen.getByTestId("delete-confirm-yes"));
  expect(await screen.findByTestId("delete-error")).toHaveTextContent(
    /ข้อมูลในเครื่องยังอยู่/,
  );
  expect(storage.stored()).toMatchObject({ userId: 7, skinType: "IV" });
});

it("clears the phone when the server user is already gone (404) or never existed", async () => {
  const storage = new MemoryStorage({
    skinType: "IV",
    userId: 7,
    deviceId: DEVICE,
    serverConsent: true,
  });
  mockDelete.mockRejectedValue(new ApiError("ไม่พบ", { status: 404 }));
  await open(storage);
  await fireEvent.press(screen.getByTestId("delete-start"));
  await fireEvent.press(screen.getByTestId("delete-confirm-yes"));
  expect(await screen.findByTestId("deleted-note")).toBeTruthy();
  expect(storage.stored()).toBeNull();
});

it("with no server user only the phone is cleared", async () => {
  const storage = new MemoryStorage({ skinType: "I" });
  await open(storage);
  await fireEvent.press(screen.getByTestId("delete-start"));
  await fireEvent.press(screen.getByTestId("delete-confirm-yes"));
  expect(await screen.findByTestId("deleted-note")).toBeTruthy();
  expect(mockDelete).not.toHaveBeenCalled();
  expect(storage.stored()).toBeNull();
});

it("withdrawing consent deletes the server record and keeps the phone settings", async () => {
  const storage = new MemoryStorage({
    skinType: "III",
    userId: 7,
    deviceId: DEVICE,
    serverConsent: true,
  });
  mockDelete.mockResolvedValue(undefined);
  await open(storage);
  await fireEvent(screen.getByTestId("consent-switch"), "valueChange", false);
  await waitFor(() => expect(storage.stored()?.userId).toBeNull());
  expect(mockDelete).toHaveBeenCalledWith(7, DEVICE);
  expect(storage.stored()).toMatchObject({
    serverConsent: false,
    skinType: "III",
  });
  await fireEvent.press(screen.getByTestId("threshold-6"));
  expect(mockUpdate).not.toHaveBeenCalled();
  expect(mockCreate).not.toHaveBeenCalled();
});

it("if the server delete fails on withdrawal, consent stays on and an error is shown", async () => {
  const storage = new MemoryStorage({
    skinType: "III",
    userId: 7,
    deviceId: DEVICE,
    serverConsent: true,
  });
  mockDelete.mockRejectedValue(new ApiError("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้"));
  await open(storage);
  await fireEvent(screen.getByTestId("consent-switch"), "valueChange", false);
  await waitFor(() =>
    expect(screen.getByTestId("sync-state")).toHaveTextContent(
      /ยังลบข้อมูลบนเซิร์ฟเวอร์ไม่ได้/,
    ),
  );
  expect(storage.stored()).toMatchObject({ serverConsent: true, userId: 7 });
});

it('day 22: the alert switch controls local alerts and works without consent', async () => {
  const N = jest.requireMock('expo-notifications');
  const storage = new MemoryStorage({ skinType: 'III', notifyEnabled: false });
  await open(storage);
  const sw = screen.getByTestId('notify-switch');
  expect(sw.props.disabled).toBeFalsy(); // no longer tied to consent
  expect(screen.queryByTestId('notify-inactive')).toBeNull();
  expect(screen.getByTestId('notify-limits')).toHaveTextContent(/อย่างน้อยวันละครั้ง/);
  expect(screen.getByTestId('notify-limits')).toHaveTextContent(/Android อาจส่งแจ้งเตือนช้ากว่าเวลาที่ตั้ง/);
  await fireEvent(sw, 'valueChange', true);
  await waitFor(() => expect(storage.stored()?.notifyEnabled).toBe(true));
  expect(storage.stored()?.serverConsent).toBe(false);
  expect(mockCreate).not.toHaveBeenCalled();
  expect(N.getPermissionsAsync).toHaveBeenCalled();
});

it('day 22: notifications not allowed by the phone are shown as such', async () => {
  const N = jest.requireMock('expo-notifications');
  N.getPermissionsAsync.mockResolvedValueOnce({ granted: false, canAskAgain: false });
  await open(new MemoryStorage({ skinType: 'III' }));
  expect(await screen.findByTestId('notify-not-allowed')).toHaveTextContent(/ยังไม่ได้อนุญาต/);
});

describe('location card and consent text (day 21)', () => {
  const Location = jest.requireMock('expo-location');

  it('consent says the province is sent, never GPS coordinates', async () => {
    await open(new MemoryStorage({ skinType: 'III' }));
    expect(screen.getByText('ยินยอมให้ส่งประเภทผิว จังหวัด และการตั้งค่าการแจ้งเตือน')).toBeTruthy();
    expect(screen.getByText(/ส่งแค่ชื่อจังหวัด ไม่ส่งพิกัด GPS/)).toBeTruthy();
  });

  it('with consent the province is synced; switching to GPS asks for permission', async () => {
    const storage = new MemoryStorage({
      skinType: 'III',
      userId: 7,
      deviceId: DEVICE,
      serverConsent: true,
      locationMode: 'province',
      province: 'ขอนแก่น',
    });
    mockUpdate.mockResolvedValue(user(7));
    await open(storage);
    expect(screen.getByTestId('settings-location')).toHaveTextContent('จ.ขอนแก่น (เลือกเอง)');
    await fireEvent.press(screen.getByTestId('threshold-11'));
    await waitFor(() => expect(mockUpdate).toHaveBeenCalled());
    expect(mockUpdate.mock.calls[0][2]).toMatchObject({ province: 'ขอนแก่น' });

    Location.requestForegroundPermissionsAsync.mockResolvedValueOnce({ status: 'denied' });
    await fireEvent.press(screen.getByTestId('settings-use-gps'));
    expect(await screen.findByTestId('settings-gps-denied')).toBeTruthy();
    expect(storage.stored()?.locationMode).toBe('province');
    await fireEvent.press(screen.getByTestId('settings-use-gps'));
    await waitFor(() => expect(storage.stored()?.locationMode).toBe('gps'));
    expect(screen.queryByTestId('settings-gps-denied')).toBeNull();
    expect(screen.getByTestId('settings-location')).toHaveTextContent(/^ตำแหน่งปัจจุบัน \(GPS\)/);
  });
});
