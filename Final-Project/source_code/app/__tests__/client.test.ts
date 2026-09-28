import {
  ApiError,
  createUser,
  deleteUser,
  fetchForecast,
  fetchPredict,
  messageForStatus,
  updateUserSettings,
} from '@/api/client';

import { sampleHours, samplePredict } from './fixtures';

const BODY = { lat: 14.02, lon: 100.52, skin_type: 'III' };

function fakeFetch(status: number, json: unknown): jest.Mock {
  return jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(json),
  });
}

it('POSTs JSON to /predict and returns the body', async () => {
  const f = fakeFetch(200, samplePredict());
  const data = await fetchPredict(BODY, { baseUrl: 'http://api.test', fetchImpl: f });
  expect(data.uvi).toBe(5.49);
  const [url, init] = f.mock.calls[0];
  expect(url).toBe('http://api.test/predict');
  expect(init.method).toBe('POST');
  expect(init.headers['Content-Type']).toBe('application/json');
  expect(JSON.parse(init.body)).toEqual(BODY);
});

it.each([502, 503, 422, 500])('maps HTTP %p to a Thai ApiError with the API detail', async (status) => {
  const f = fakeFetch(status, { detail: 'Open-Meteo returned no usable hours' });
  const err = await fetchPredict(BODY, { baseUrl: 'http://api.test', fetchImpl: f }).catch((e) => e);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.status).toBe(status);
  expect(err.message).toBe(messageForStatus(status));
  expect(err.url).toBe('http://api.test/predict');
  expect(err.detail).toBe(`HTTP ${status}: Open-Meteo returned no usable hours`);
});

it('reports a network failure in Thai with the URL and the original error', async () => {
  const f = jest.fn().mockRejectedValue(new TypeError('Network request failed'));
  const err = await fetchPredict(BODY, { baseUrl: 'http://192.168.1.48:8000', fetchImpl: f }).catch(
    (e) => e,
  );
  expect(err.message).toContain('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้');
  expect(err.url).toBe('http://192.168.1.48:8000/predict');
  expect(err.detail).toBe('TypeError: Network request failed');
});

it('times out slow responses', async () => {
  const f = jest.fn(
    (_url: string, init: RequestInit) =>
      new Promise((_res, rej) => init.signal!.addEventListener('abort', () => rej(new Error('aborted')))),
  ) as unknown as typeof fetch;
  const err = await fetchPredict(BODY, { fetchImpl: f, timeoutMs: 10 }).catch((e) => e);
  expect(err.message).toContain('เซิร์ฟเวอร์ตอบช้าเกินไป');
  expect(err.detail).toMatch(/^timeout after 0.01 s/);
});

it('rejects a body that is not a predict response', async () => {
  const f = fakeFetch(200, { hello: 1 });
  await expect(fetchPredict(BODY, { fetchImpl: f })).rejects.toThrow('รูปแบบข้อมูล');
});

describe('API_URL from EXPO_PUBLIC_API_URL', () => {
  const saved = process.env.EXPO_PUBLIC_API_URL;
  afterEach(() => {
    if (saved === undefined) delete process.env.EXPO_PUBLIC_API_URL;
    else process.env.EXPO_PUBLIC_API_URL = saved;
  });

  it('uses the variable (trailing slash removed) and falls back to localhost:8000', () => {
    process.env.EXPO_PUBLIC_API_URL = 'http://192.168.1.48:8000/';
    jest.isolateModules(() => {
      expect(require('@/config').API_URL).toBe('http://192.168.1.48:8000');
    });
    delete process.env.EXPO_PUBLIC_API_URL;
    jest.isolateModules(() => {
      expect(require('@/config').API_URL).toBe('http://localhost:8000');
    });
  });
});

it('GETs /forecast with lat, lon and hours', async () => {
  const hours = sampleHours('2026-09-27T20:00:00+07:00', [0, 1, 2]);
  const f = fakeFetch(200, { lat: 14.02, lon: 100.52, hours, note: null, disclaimer: 'd' });
  const fc = await fetchForecast(14.02, 100.52, 36, { baseUrl: 'http://api.test', fetchImpl: f });
  expect(fc.hours).toHaveLength(3);
  const [url, init] = f.mock.calls[0];
  expect(url).toBe('http://api.test/forecast?lat=14.02&lon=100.52&hours=36');
  expect(init.method).toBe('GET');
});

it('forecast errors carry the URL and the API detail', async () => {
  const f = fakeFetch(502, { detail: 'Open-Meteo unavailable: ConnectionError' });
  const err = await fetchForecast(14.02, 100.52, 36, {
    baseUrl: 'http://api.test',
    fetchImpl: f,
  }).catch((e) => e);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.url).toBe('http://api.test/forecast?lat=14.02&lon=100.52&hours=36');
  expect(err.detail).toBe('HTTP 502: Open-Meteo unavailable: ConnectionError');
});

describe('/users', () => {
  const DEV = '11111111-2222-4333-8444-555555555555';
  const USER = { id: 5, skin_type: 'III', alert_threshold: 8, safe_threshold: 6 };

  it('POST /users sends the device id only in the X-Device-Id header', async () => {
    const f = fakeFetch(201, USER);
    const u = await createUser(DEV, { skin_type: 'III', alert_threshold: 8 }, {
      baseUrl: 'http://api.test',
      fetchImpl: f,
    });
    expect(u.id).toBe(5);
    const [url, init] = f.mock.calls[0];
    expect(url).toBe('http://api.test/users');
    expect(init.method).toBe('POST');
    expect(init.headers['X-Device-Id']).toBe(DEV);
    expect(init.body).not.toContain(DEV);
  });

  it('PUT /users/{id}/settings and DELETE /users/{id} (204, no body)', async () => {
    const put = fakeFetch(200, USER);
    await updateUserSettings(5, DEV, { alert_threshold: 11 }, {
      baseUrl: 'http://api.test',
      fetchImpl: put,
    });
    expect(put.mock.calls[0][0]).toBe('http://api.test/users/5/settings');
    expect(put.mock.calls[0][1]).toMatchObject({ method: 'PUT' });
    expect(JSON.parse(put.mock.calls[0][1].body)).toEqual({ alert_threshold: 11 });

    const json = jest.fn();
    const del = jest.fn().mockResolvedValue({ ok: true, status: 204, json });
    await expect(
      deleteUser(5, DEV, { baseUrl: 'http://api.test', fetchImpl: del }),
    ).resolves.toBeUndefined();
    expect(del.mock.calls[0][0]).toBe('http://api.test/users/5');
    expect(del.mock.calls[0][1]).toMatchObject({ method: 'DELETE', headers: { 'X-Device-Id': DEV } });
    expect(json).not.toHaveBeenCalled();
  });

  it.each([
    [403, 'อุปกรณ์นี้ไม่มีสิทธิ์แก้ข้อมูลผู้ใช้นี้'],
    [404, 'ไม่พบข้อมูลผู้ใช้บนเซิร์ฟเวอร์'],
  ])('maps HTTP %p to a Thai message', async (status, message) => {
    const f = fakeFetch(status, { detail: 'x' });
    const err = await deleteUser(5, DEV, { baseUrl: 'http://api.test', fetchImpl: f }).catch(
      (e) => e,
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(status);
    expect(err.message).toBe(message);
  });
});
