/**
 * Minimal client for the UV Guard API (day 18: POST /predict only).
 */

import { API_URL, REQUEST_TIMEOUT_MS } from '@/config';

import type { PredictRequest, PredictResponse } from './types';

/** Error with a Thai message that can be shown to the user as-is. */
export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
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

type FetchOptions = {
  baseUrl?: string;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
};

/** Current UV estimate, range, risk and forecast for one location and skin type. */
export async function fetchPredict(
  body: PredictRequest,
  { baseUrl = API_URL, timeoutMs = REQUEST_TIMEOUT_MS, fetchImpl = fetch }: FetchOptions = {},
): Promise<PredictResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetchImpl(`${baseUrl}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch {
    if (controller.signal.aborted) {
      throw new ApiError('เซิร์ฟเวอร์ตอบช้าเกินไป ลองใหม่อีกครั้ง');
    }
    throw new ApiError('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจอินเทอร์เน็ตหรือที่อยู่ API');
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    throw new ApiError(messageForStatus(res.status), res.status);
  }
  const data = (await res.json()) as PredictResponse;
  if (typeof data?.uvi !== 'number' || !Array.isArray(data?.uvi_range)) {
    throw new ApiError('รูปแบบข้อมูลจากเซิร์ฟเวอร์ไม่ถูกต้อง');
  }
  return data;
}
