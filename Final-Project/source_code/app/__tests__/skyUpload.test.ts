/**
 * Sky photo upload through expo/fetch (Expo Go Android bug, 29 Sep 2026): on native, SDK 57
 * replaces global fetch with expo/fetch, whose convertFormDataAsync accepts only strings, Blobs
 * and objects with bytes(); a React Native `{ uri, name, type }` part throws
 * "Unsupported FormDataPart implementation" before any request is sent. These tests run the
 * REAL expo converter on the form the app builds, with FormData behaving as on the phone.
 */

import { convertFormDataAsync } from 'expo/src/winter/fetch/convertFormData';
import { File } from 'expo-file-system';

import { ApiError, PREPARE_FAILED_TH, skyImageForm, uploadSkyImage } from '@/api/client';

import { sampleSky } from './fixtures_sky';

// On the phone the global FormData is React Native's, patched by expo's installFormDataPatch
// (runtime.native.ts): append keeps the value as is and entries() yields the [name, value] parts.
// Jest's global is Node's (undici), which stringifies unknown parts, and expo's patch is a no-op
// under jest-expo, so this subclass reproduces exactly that phone behaviour.
const RNFormData = jest.requireActual('react-native/Libraries/Network/FormData').default;
class PhoneFormData extends RNFormData {
  entries() {
    return (this as unknown as { _parts: [string, unknown][] })._parts[Symbol.iterator]();
  }
}
(globalThis as { FormData: unknown }).FormData = PhoneFormData;

const decode = (b: Uint8Array) => Array.from(b, (c) => String.fromCharCode(c)).join('');

it('native form is accepted by the real expo/fetch converter (bytes of the file are sent)', async () => {
  const form = await skyImageForm('file:///cache/ImageManipulator/clean.jpg', {
    platform: 'android',
    makeFile: (uri) => new File(uri),
  });
  const { body, boundary } = await convertFormDataAsync(form, '----test');
  const text = decode(body);
  expect(boundary).toBe('----test');
  expect(text).toContain('content-disposition: form-data; name="file"; filename="clean.jpg"');
  expect(text).toContain('content-type: image/jpeg');
  expect(Array.from(body)).toEqual(expect.arrayContaining([0xff, 0xd8, 0xff, 0xd9]));
});

it('the old React Native {uri, name, type} part is what expo/fetch rejects (the cause)', async () => {
  const form = new FormData();
  form.append('file', { uri: 'file:///c.jpg', name: 'sky.jpg', type: 'image/jpeg' } as unknown as Blob);
  await expect(convertFormDataAsync(form)).rejects.toThrow('Unsupported FormDataPart implementation');
});

function fakeFetch(status: number, body: unknown) {
  return jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  }) as unknown as jest.Mock & typeof fetch;
}

it('a body that cannot be built is a "prepare" error and fetch is never called', async () => {
  const f = fakeFetch(200, sampleSky());
  const err = await uploadSkyImage('file:///c.jpg', {
    fetchImpl: f,
    platform: 'android',
    // the pre-fix React Native part: expo/fetch would reject it inside fetch
    makeFile: (uri) => ({ uri, name: 'sky.jpg', type: 'image/jpeg' }) as unknown as Blob,
  }).catch((e) => e);
  expect(f).not.toHaveBeenCalled();
  expect(err).toBeInstanceOf(ApiError);
  expect(err.stage).toBe('prepare');
  expect(err.message).toBe(PREPARE_FAILED_TH);
  expect(err.message).not.toMatch(/เชื่อมต่อ/);
  expect(err.detail).toMatch(/cannot be sent/);
  const failing = await uploadSkyImage('file:///c.jpg', {
    fetchImpl: f,
    platform: 'android',
    makeFile: () => {
      throw new Error('file gone');
    },
  }).catch((e) => e);
  expect(failing.stage).toBe('prepare');
  expect(f).not.toHaveBeenCalled();
});

