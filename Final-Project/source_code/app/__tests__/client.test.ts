import { ApiError, fetchPredict, messageForStatus } from '@/api/client';

import { samplePredict } from './fixtures';

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

it.each([502, 503, 422, 500])('maps HTTP %p to a Thai ApiError', async (status) => {
  const f = fakeFetch(status, { detail: 'x' });
  const err = await fetchPredict(BODY, { fetchImpl: f }).catch((e) => e);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.status).toBe(status);
  expect(err.message).toBe(messageForStatus(status));
});

it('reports a network failure in Thai', async () => {
  const f = jest.fn().mockRejectedValue(new TypeError('Network request failed'));
  await expect(fetchPredict(BODY, { fetchImpl: f })).rejects.toThrow('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้');
});

it('times out slow responses', async () => {
  const f = jest.fn(
    (_url: string, init: RequestInit) =>
      new Promise((_res, rej) => init.signal!.addEventListener('abort', () => rej(new Error('aborted')))),
  ) as unknown as typeof fetch;
  await expect(fetchPredict(BODY, { fetchImpl: f, timeoutMs: 10 })).rejects.toThrow(
    'เซิร์ฟเวอร์ตอบช้าเกินไป',
  );
});

it('rejects a body that is not a predict response', async () => {
  const f = fakeFetch(200, { hello: 1 });
  await expect(fetchPredict(BODY, { fetchImpl: f })).rejects.toThrow('รูปแบบข้อมูล');
});
