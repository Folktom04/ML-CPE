import {
  ApiError,
  messageForStatus,
  skyImageForm,
  uploadSkyImage,
} from '@/api/client';
import { cloudLevelTh, LOW_CONFIDENCE, pct, rankedClasses, skyView } from '@/lib/sky';
import { analyzeSkyPhoto, reencodePhoto, removeTempFile, type SkyPhotoDeps } from '@/lib/skyPhoto';

import { sampleSky, unsureSky } from './fixtures_sky';

const manip = jest.requireMock('expo-image-manipulator');
const fs = jest.requireMock('expo-file-system');

function fakeFetch(status: number, json: unknown): jest.Mock {
  return jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(json),
  });
}

beforeEach(() => {
  fs.__deleted.length = 0;
  manip.ImageManipulator.manipulate.mockClear();
  manip.__ctx.resize.mockClear();
});

describe('skyView', () => {
  it('confident answer shows the class', () => {
    expect(skyView(sampleSky(0.87))).toEqual({
      kind: 'sure',
      nameTh: 'เมฆหนาสีขาว',
      confidence: 0.87,
      cloudFraction: 0.62,
      cloudFractionCnn: null, // the API did not send the SWIMSEG head
    });
    expect(skyView({ ...sampleSky(0.87), cloud_fraction_cnn: 0.55 }).cloudFractionCnn).toBe(0.55);
    expect(skyView(sampleSky(LOW_CONFIDENCE)).kind).toBe('sure'); // 0.5 itself is not "unsure"
  });

  it('below 0.5 is "unsure" with the top 2 classes in Thai', () => {
    const v = skyView(unsureSky());
    expect(v.kind).toBe('unsure');
    if (v.kind !== 'unsure') return;
    expect(v.top.map((c) => [c.nameTh, c.prob])).toEqual([
      ['เมฆบางคลุมทั่วฟ้า', 0.41],
      ['เมฆบางสีขาว', 0.33],
    ]);
  });

  it('unknown class ids fall back to the id, and percentages round', () => {
    expect(rankedClasses({ new_class: 0.2 })[0].nameTh).toBe('new_class');
    expect(pct(0.874)).toBe('87%');
  });
});

describe('uploadSkyImage', () => {
  it('POSTs multipart with the file part and no JSON content type', async () => {
    const f = fakeFetch(200, sampleSky());
    const data = await uploadSkyImage('file:///c/clean.jpg', {
      baseUrl: 'http://api.test',
      fetchImpl: f,
      platform: 'android',
    });
    expect(data.sky_class_th).toBe('เมฆหนาสีขาว');
    const [url, init] = f.mock.calls[0];
    expect(url).toBe('http://api.test/sky-image');
    expect(init.method).toBe('POST');
    expect(init.headers).toBeUndefined();
    expect(init.body).toBeInstanceOf(FormData);
  });

  it('native form sends an expo-file-system File (not {uri}); web form reads the blob', async () => {
    const { File } = jest.requireMock('expo-file-system');
    const append = jest.spyOn(FormData.prototype, 'append').mockImplementation(() => undefined);
    await skyImageForm('file:///c/clean.jpg', { platform: 'android' });
    const [name, part, filename] = append.mock.calls[append.mock.calls.length - 1];
    expect(name).toBe('file');
    expect(part).toBeInstanceOf(File);
    expect((part as unknown as { uri: string }).uri).toBe('file:///c/clean.jpg');
    expect(part).not.toHaveProperty('uri', undefined);
    expect(filename).toBeUndefined(); // expo's FormData would re-wrap the part otherwise
    const blob = new Blob(['x'], { type: 'image/jpeg' });
    const f = jest.fn().mockResolvedValue({ blob: () => Promise.resolve(blob) });
    await skyImageForm('blob:http://localhost/1', { platform: 'web', fetchImpl: f });
    expect(f).toHaveBeenCalledWith('blob:http://localhost/1');
    expect(append).toHaveBeenLastCalledWith('file', blob, 'sky.jpg');
    append.mockRestore();
  });

  it.each([413, 415])('HTTP %p gives a Thai message', async (status) => {
    const f = fakeFetch(status, { detail: 'x' });
    const err = await uploadSkyImage('file:///c.jpg', { fetchImpl: f, platform: 'android' }).catch(
      (e) => e,
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe(messageForStatus(status));
    expect(messageForStatus(413)).toBe('รูปใหญ่เกิน 10 MB');
    expect(messageForStatus(415)).toContain('ไม่ใช่รูปภาพ');
  });

  it('a real network failure is still "cannot connect" (no prepare stage)', async () => {
    const f = jest.fn().mockRejectedValue(new TypeError('Network request failed'));
    const err = await uploadSkyImage('file:///c.jpg', {
      fetchImpl: f as unknown as typeof fetch,
      platform: 'android',
    }).catch((e) => e);
    expect(f).toHaveBeenCalledTimes(1);
    expect(err.stage).toBeUndefined();
    expect(err.message).toBe('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจอินเทอร์เน็ตหรือที่อยู่ API');
  });

  it('rejects a response without the sky fields', async () => {
    const f = fakeFetch(200, { sky_class: 'clear_sky' });
    const err = await uploadSkyImage('file:///c.jpg', { fetchImpl: f, platform: 'android' }).catch(
      (e) => e,
    );
    expect(err.message).toBe('รูปแบบข้อมูลจากเซิร์ฟเวอร์ไม่ถูกต้อง');
  });
});

describe('analyzeSkyPhoto (EXIF removal + temp files)', () => {
  const photo = { uri: 'file:///cache/original.jpg', width: 3000, height: 4000 };

  function deps(upload: SkyPhotoDeps['upload']) {
    const removed: string[] = [];
    const d: SkyPhotoDeps = {
      reencode: jest.fn(async () => 'file:///cache/clean.jpg'),
      upload,
      remove: (u) => removed.push(u),
    };
    return { d, removed };
  }

  it('uploads only the re-encoded file and deletes both files', async () => {
    const upload = jest.fn(async () => sampleSky());
    const { d, removed } = deps(upload);
    await analyzeSkyPhoto(photo, d);
    expect(d.reencode).toHaveBeenCalledWith(photo);
    expect(upload).toHaveBeenCalledWith('file:///cache/clean.jpg');
    expect(removed).toEqual(['file:///cache/original.jpg', 'file:///cache/clean.jpg']);
  });

  it('still deletes both files when the upload fails', async () => {
    const { d, removed } = deps(() => Promise.reject(new ApiError('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้')));
    await expect(analyzeSkyPhoto(photo, d)).rejects.toThrow('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้');
    expect(removed).toEqual(['file:///cache/original.jpg', 'file:///cache/clean.jpg']);
  });

  it('still deletes the original when re-encoding fails (nothing is uploaded)', async () => {
    const upload = jest.fn();
    const { d, removed } = deps(upload);
    d.reencode = () => Promise.reject(new Error('out of memory'));
    await expect(analyzeSkyPhoto(photo, d)).rejects.toThrow('out of memory');
    expect(upload).not.toHaveBeenCalled();
    expect(removed).toEqual(['file:///cache/original.jpg']);
  });

  it('default re-encode: fresh JPEG, longest side 1024, always re-encoded', async () => {
    const out = await reencodePhoto(photo);
    expect(out).toBe('file:///cache/ImageManipulator/clean.jpg');
    expect(manip.ImageManipulator.manipulate).toHaveBeenCalledWith(photo.uri);
    expect(manip.__ctx.resize).toHaveBeenCalledWith({ height: 1024 }); // portrait
    await reencodePhoto({ uri: 'file:///s.jpg', width: 800, height: 600 });
    expect(manip.ImageManipulator.manipulate).toHaveBeenCalledTimes(2); // small: still re-encoded
    expect(manip.__ctx.resize).toHaveBeenCalledTimes(1); // ... but not resized
  });

  it('removeTempFile deletes file:// files, skips web URLs and never throws', () => {
    expect(removeTempFile('file:///cache/clean.jpg')).toBe(true);
    expect(fs.__deleted).toEqual(['file:///cache/clean.jpg']);
    expect(removeTempFile('blob:http://localhost/1')).toBe(false); // web: nothing on disk
    const spy = jest.spyOn(fs.File.prototype, 'delete').mockImplementation(() => {
      throw new Error('busy');
    });
    expect(removeTempFile('file:///x.jpg')).toBe(false);
    spy.mockRestore();
  });
});

describe('cloudLevelTh (SWIMSEG head shown as a level, not a percentage)', () => {
  it.each([
    [0, 'น้อย'],
    [0.15, 'น้อย'], // what a clear photo typically gets from the head
    [0.2999, 'น้อย'],
    [0.3, 'ปานกลาง'],
    [0.55, 'ปานกลาง'],
    [0.7, 'ปานกลาง'],
    [0.7001, 'มาก'],
    [1, 'มาก'],
  ])('%p → %p', (f, level) => {
    expect(cloudLevelTh(f)).toBe(level);
  });
});
