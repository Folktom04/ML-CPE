/**
 * Minimal client for the UV Guard API (day 18: POST /predict, GET /forecast; day 19: /users;
 * day 20: POST /sky-image; day 23: PUT /users/{id}/push-token, GET /health).
 */

import { File } from 'expo-file-system';
import { Platform } from 'react-native';

import { API_URL, REQUEST_TIMEOUT_MS } from '@/config';

import type {
  ForecastResponse,
  HealthResponse,
  PredictRequest,
  PredictResponse,
  PushTokenResponse,
  SkyImageResponse,
  UserResponse,
  UserSettingsBody,
} from './types';

/**
 * Error with a Thai message that can be shown to the user as-is, plus debug details:
 * the URL that was called and the original error text (e.g. "TypeError: Network request failed").
 */
export class ApiError extends Error {
  status?: number;
  url?: string;
  detail?: string;
  /** 'prepare' = failed while building the request on the phone; nothing was sent. */
  stage?: 'prepare';

  constructor(
    message: string,
    opts: { status?: number; url?: string; detail?: string; stage?: 'prepare' } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = opts.status;
    this.url = opts.url;
    this.detail = opts.detail;
    this.stage = opts.stage;
  }
}

/** Shown when the request body could not be built: an app problem, not the internet. */
export const PREPARE_FAILED_TH =
  'แอปเตรียมรูปเพื่อส่งไม่สำเร็จ ยังไม่ได้ส่งข้อมูลไปเซิร์ฟเวอร์ (เป็นปัญหาในแอป ไม่ใช่อินเทอร์เน็ต)';

/** Thai message for an HTTP error status of the API. */
export function messageForStatus(status: number): string {
  switch (status) {
    case 502:
      return 'ดึงข้อมูลสภาพอากาศจาก Open-Meteo ไม่ได้ ลองใหม่อีกครั้ง';
    case 503:
      return 'ข้อมูลสภาพอากาศของชั่วโมงนี้ยังไม่มา ลองใหม่ภายหลัง';
    case 400:
      return 'รหัสอุปกรณ์ไม่ถูกต้อง';
    case 403:
      return 'อุปกรณ์นี้ไม่มีสิทธิ์แก้ข้อมูลผู้ใช้นี้';
    case 404:
      return 'ไม่พบข้อมูลผู้ใช้บนเซิร์ฟเวอร์';
    case 413:
      return 'รูปใหญ่เกิน 10 MB';
    case 415:
      return 'ไฟล์นี้ไม่ใช่รูปภาพ หรือเปิดอ่านไม่ได้';
    case 422:
      return 'ข้อมูลตำแหน่งหรือประเภทผิวไม่ถูกต้อง';
    default:
      return `เซิร์ฟเวอร์ขัดข้อง (รหัส ${status}) ลองใหม่อีกครั้ง`;
  }
}

/** "Name: message" of any thrown value, for the debug line. */
export function describeError(err: unknown): string {
  if (err instanceof Error) return `${err.name}: ${err.message}`;
  return String(err);
}

/** The API's `detail` field of an error body, if it is readable. */
async function errorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    const d = body?.detail;
    return typeof d === 'string' ? d : JSON.stringify(d);
  } catch {
    return '';
  }
}

type FetchOptions = {
  baseUrl?: string;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
};

/** fetch with timeout; errors become ApiError with the URL and the original error text. */
async function request(
  url: string,
  init: RequestInit,
  { timeoutMs = REQUEST_TIMEOUT_MS, fetchImpl = fetch }: FetchOptions,
): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetchImpl(url, { ...init, signal: controller.signal });
  } catch (err) {
    if (controller.signal.aborted) {
      throw new ApiError('เซิร์ฟเวอร์ตอบช้าเกินไป ลองใหม่อีกครั้ง', {
        url,
        detail: `timeout after ${timeoutMs / 1000} s (${describeError(err)})`,
      });
    }
    throw new ApiError('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจอินเทอร์เน็ตหรือที่อยู่ API', {
      url,
      detail: describeError(err),
    });
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    const detail = await errorDetail(res);
    // A Thai `detail` from the API (e.g. 422 "รองรับเฉพาะพื้นที่ประเทศไทย") is shown as is.
    const thai = /[\u0E00-\u0E7F]/.test(detail) && !detail.startsWith('[') ? detail : null;
    throw new ApiError(thai ?? messageForStatus(res.status), {
      status: res.status,
      url,
      detail: `HTTP ${res.status}${detail ? `: ${detail}` : ''}`,
    });
  }
  if (res.status === 204) return null;
  return res.json();
}

/** Current UV estimate, range, risk and forecast for one location and skin type. */
export async function fetchPredict(
  body: PredictRequest,
  { baseUrl = API_URL, ...opts }: FetchOptions = {},
): Promise<PredictResponse> {
  const url = `${baseUrl}/predict`;
  const data = (await request(
    url,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    opts,
  )) as PredictResponse;
  if (typeof data?.uvi !== 'number' || !Array.isArray(data?.uvi_range)) {
    throw new ApiError('รูปแบบข้อมูลจากเซิร์ฟเวอร์ไม่ถูกต้อง', {
      url,
      detail: 'response has no uvi / uvi_range',
    });
  }
  return data;
}

/** Hourly forecast from now (1-36 h; Asia/Bangkok local start of each hour). */
export async function fetchForecast(
  lat: number,
  lon: number,
  hours = 36,
  { baseUrl = API_URL, ...opts }: FetchOptions = {},
): Promise<ForecastResponse> {
  const url = `${baseUrl}/forecast?lat=${lat}&lon=${lon}&hours=${hours}`;
  const data = (await request(url, { method: 'GET' }, opts)) as ForecastResponse;
  if (!Array.isArray(data?.hours)) {
    throw new ApiError('รูปแบบข้อมูลจากเซิร์ฟเวอร์ไม่ถูกต้อง', {
      url,
      detail: 'response has no hours',
    });
  }
  return data;
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };

/**
 * Register this phone (idempotent per device id). The device id is sent only in the
 * X-Device-Id header and never shown on screen.
 */
export async function createUser(
  deviceId: string,
  body: UserSettingsBody & { skin_type: string },
  { baseUrl = API_URL, ...opts }: FetchOptions = {},
): Promise<UserResponse> {
  return (await request(
    `${baseUrl}/users`,
    {
      method: 'POST',
      headers: { ...JSON_HEADERS, 'X-Device-Id': deviceId },
      body: JSON.stringify(body),
    },
    opts,
  )) as UserResponse;
}

/** Change some settings of the user (only the owner's device id is accepted). */
export async function updateUserSettings(
  userId: number,
  deviceId: string,
  body: UserSettingsBody,
  { baseUrl = API_URL, ...opts }: FetchOptions = {},
): Promise<UserResponse> {
  return (await request(
    `${baseUrl}/users/${userId}/settings`,
    {
      method: 'PUT',
      headers: { ...JSON_HEADERS, 'X-Device-Id': deviceId },
      body: JSON.stringify(body),
    },
    opts,
  )) as UserResponse;
}

/** Delete the user and all of their data on the server (204). */
export async function deleteUser(
  userId: number,
  deviceId: string,
  { baseUrl = API_URL, ...opts }: FetchOptions = {},
): Promise<void> {
  await request(
    `${baseUrl}/users/${userId}`,
    { method: 'DELETE', headers: { 'X-Device-Id': deviceId } },
    opts,
  );
}

/**
 * Day 23: store this phone's Expo push token for server push (only the owner's device id is
 * accepted). The server never echoes the token back.
 */
export async function registerPushToken(
  userId: number,
  deviceId: string,
  token: string,
  platform: string,
  { baseUrl = API_URL, ...opts }: FetchOptions = {},
): Promise<PushTokenResponse> {
  return (await request(
    `${baseUrl}/users/${userId}/push-token`,
    {
      method: 'PUT',
      headers: { ...JSON_HEADERS, 'X-Device-Id': deviceId },
      body: JSON.stringify({ token, platform }),
    },
    opts,
  )) as PushTokenResponse;
}

/** GET /health: server status, including whether the push scheduler runs (day 23). */
export async function getHealth({
  baseUrl = API_URL,
  ...opts
}: FetchOptions = {}): Promise<HealthResponse> {
  return (await request(`${baseUrl}/health`, { method: 'GET' }, opts)) as HealthResponse;
}

/** A file part that expo/fetch can read (expo-file-system `File` implements Blob via bytes()). */
type UploadFile = Blob | { bytes(): Promise<Uint8Array>; name?: string; type?: string };

/**
 * Multipart body with the photo at `uri` (a JPEG already re-encoded without EXIF).
 *
 * On a phone SDK 57 replaces global fetch with expo/fetch, whose FormData converter accepts only
 * strings, Blobs and objects with `bytes()`; the old React Native `{ uri, name, type }` part makes
 * it throw "Unsupported FormDataPart implementation" before anything is sent. So the phone
 * attaches an expo-file-system `File` (read with `bytes()`, name and MIME type from the file).
 * No third filename argument: expo's FormData would re-wrap the part. On the web the uri is a
 * blob:/data: URL, so the bytes are read into a Blob first.
 */
export async function skyImageForm(
  uri: string,
  {
    platform = Platform.OS,
    fetchImpl = fetch,
    makeFile = (u: string): UploadFile => new File(u),
  }: { platform?: string; fetchImpl?: typeof fetch; makeFile?: (uri: string) => UploadFile } = {},
): Promise<FormData> {
  const form = new FormData();
  if (platform === 'web') {
    const blob = await (await fetchImpl(uri)).blob();
    form.append('file', blob, 'sky.jpg');
  } else {
    form.append('file', makeFile(uri) as Blob);
  }
  return form;
}

/**
 * Throw unless every part is one expo/fetch can encode (a string, a Blob or has `bytes()`): the
 * same rule as its converter, checked BEFORE fetch so a bad body is never reported as a
 * connection problem. Forms without `entries()` are left to fetch.
 */
export function assertUploadableForm(form: FormData): void {
  const entries = (form as unknown as { entries?: () => Iterable<[string, unknown]> }).entries;
  if (typeof entries !== 'function') return;
  for (const [name, value] of entries.call(form)) {
    const ok =
      typeof value === 'string' ||
      (typeof Blob !== 'undefined' && value instanceof Blob) ||
      (typeof value === 'object' && value !== null && 'bytes' in value);
    if (!ok) throw new Error(`form part "${name}" cannot be sent (no bytes/Blob)`);
  }
}

/** Sky class + cloud fraction of a sky photo (processed in memory by the API, never stored). */
export async function uploadSkyImage(
  uri: string,
  {
    baseUrl = API_URL,
    platform,
    makeFile,
    ...opts
  }: FetchOptions & { platform?: string; makeFile?: (uri: string) => UploadFile } = {},
): Promise<SkyImageResponse> {
  const url = `${baseUrl}/sky-image`;
  let body: FormData;
  try {
    body = await skyImageForm(uri, { platform, fetchImpl: opts.fetchImpl, makeFile });
    assertUploadableForm(body);
  } catch (err) {
    // stage "prepare": failed on the phone before the request, so never "cannot connect"
    throw new ApiError(PREPARE_FAILED_TH, { url, detail: describeError(err), stage: 'prepare' });
  }
  // no Content-Type header: fetch sets multipart/form-data with the boundary itself
  const data = (await request(url, { method: 'POST', body }, opts)) as SkyImageResponse;
  if (
    typeof data?.sky_class_th !== 'string' ||
    typeof data?.sky_confidence !== 'number' ||
    typeof data?.cloud_fraction_rb !== 'number' ||
    typeof data?.sky_class_probs !== 'object'
  ) {
    throw new ApiError('รูปแบบข้อมูลจากเซิร์ฟเวอร์ไม่ถูกต้อง', {
      url,
      detail: 'response has no sky_class_th / sky_confidence / cloud_fraction_rb',
    });
  }
  return data;
}
