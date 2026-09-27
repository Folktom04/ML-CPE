/**
 * Minimal client for the UV Guard API (day 18: POST /predict, GET /forecast).
 */

import { API_URL, REQUEST_TIMEOUT_MS } from '@/config';

import type { ForecastResponse, PredictRequest, PredictResponse } from './types';

/**
 * Error with a Thai message that can be shown to the user as-is, plus debug details:
 * the URL that was called and the original error text (e.g. "TypeError: Network request failed").
 */
export class ApiError extends Error {
  status?: number;
  url?: string;
  detail?: string;

  constructor(message: string, opts: { status?: number; url?: string; detail?: string } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = opts.status;
    this.url = opts.url;
    this.detail = opts.detail;
  }
}

/** Thai message for an HTTP error status of the API. */
export function messageForStatus(status: number): string {
  switch (status) {
    case 502:
      return 'ดึงข้อมูลสภาพอากาศจาก Open-Meteo ไม่ได้ ลองใหม่อีกครั้ง';
    case 503:
      return 'ข้อมูลสภาพอากาศของชั่วโมงนี้ยังไม่มา ลองใหม่ภายหลัง';
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
    throw new ApiError(messageForStatus(res.status), {
      status: res.status,
      url,
      detail: `HTTP ${res.status}${detail ? `: ${detail}` : ''}`,
    });
  }
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
