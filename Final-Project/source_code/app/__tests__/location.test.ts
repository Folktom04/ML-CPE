import * as Location from 'expo-location';

import {
  fallbackPlace,
  LOCATION_TIMEOUT_MS,
  requestLocationPermission,
  resolvePlace,
  roundCoord,
} from '@/lib/location';
import {
  distanceKm,
  findProvince,
  nearestProvince,
  PROVINCE_SOURCE,
  PROVINCES,
  searchProvinces,
} from '@/lib/provinces';
import { DEFAULT_SETTINGS, type Settings } from '@/lib/settings';

const L = jest.mocked(Location);
const settings = (patch: Partial<Settings> = {}): Settings => ({ ...DEFAULT_SETTINGS, ...patch });

beforeEach(() => {
  jest.clearAllMocks();
  L.getForegroundPermissionsAsync.mockResolvedValue({ status: 'granted' } as never);
  L.getLastKnownPositionAsync.mockResolvedValue(null);
  L.getCurrentPositionAsync.mockResolvedValue({
    coords: { latitude: 13.75634, longitude: 100.50177 },
  } as never);
});

describe('provinces', () => {
  it('has the 77 provinces from the geocoding table, with its licence', () => {
    expect(PROVINCES).toHaveLength(77);
    expect(new Set(PROVINCES.map((p) => p.name_th)).size).toBe(77);
    expect(PROVINCE_SOURCE).toBe('Open-Meteo Geocoding API (GeoNames, CC BY 4.0)');
    expect(findProvince('ปทุมธานี')).toMatchObject({ name_en: 'Pathum Thani' });
    expect(findProvince('ไม่มีจังหวัดนี้')).toBeNull();
    expect(findProvince(null)).toBeNull();
  });

  it('distance matches src/inference.py distance_km', () => {
    expect(distanceKm(13.75, 100.5, 14.02, 100.52)).toBeCloseTo(30.1, 0);
    expect(distanceKm(18.79, 98.98, 14.02, 100.52)).toBeGreaterThan(550);
  });

  it.each([
    [13.7563, 100.5018, 'กรุงเทพมหานคร'],
    [18.7883, 98.9853, 'เชียงใหม่'],
    [7.0086, 100.4747, 'สงขลา'], // Hat Yai
    [14.0208, 100.525, 'ปทุมธานี'],
  ])('nearest province of (%p, %p) is %p', (lat, lon, name) => {
    expect(nearestProvince(lat, lon).name_th).toBe(name);
  });

  it('searches Thai and English names, ignoring case and spaces', () => {
    expect(searchProvinces('เชียง').map((p) => p.name_th)).toEqual(['เชียงราย', 'เชียงใหม่']);
    expect(searchProvinces('chiang mai').map((p) => p.name_th)).toEqual(['เชียงใหม่']);
    expect(searchProvinces('  ')).toHaveLength(77);
    expect(searchProvinces('zzz')).toEqual([]);
  });
});

describe('location', () => {
  it('rounds coordinates to 0.01 deg (about 1 km)', () => {
    expect(roundCoord(14.02083)).toBe(14.02);
    expect(roundCoord(100.52504)).toBe(100.53);
    expect(roundCoord(-0.004)).toBe(-0);
  });

  it('asks for "while using" permission only and never throws', async () => {
    expect(await requestLocationPermission()).toBe(true);
    L.requestForegroundPermissionsAsync.mockResolvedValueOnce({ status: 'denied' } as never);
    expect(await requestLocationPermission()).toBe(false);
    L.requestForegroundPermissionsAsync.mockRejectedValueOnce(new Error('boom'));
    expect(await requestLocationPermission()).toBe(false);
  });

  it('with nothing chosen uses Pathum Thani without touching GPS', async () => {
    const p = await resolvePlace(settings());
    expect(p).toMatchObject({ lat: 14.02, lon: 100.52, source: 'default', notice: null });
    expect(p.label).toBe('ปทุมธานี (ตำแหน่งเริ่มต้น)');
    expect(L.getForegroundPermissionsAsync).not.toHaveBeenCalled();
  });

  it('a chosen province uses its capital', async () => {
    const p = await resolvePlace(settings({ locationMode: 'province', province: 'เชียงใหม่' }));
    expect(p).toMatchObject({ lat: 18.79, lon: 98.98, source: 'province', province: 'เชียงใหม่' });
    expect(p.label).toBe('จ.เชียงใหม่ (เลือกเอง)');
    expect(L.getCurrentPositionAsync).not.toHaveBeenCalled();
  });

  it('GPS: rounded fix, nearest province, no notice', async () => {
    const p = await resolvePlace(settings({ locationMode: 'gps' }));
    expect(p).toMatchObject({ lat: 13.76, lon: 100.5, source: 'gps', province: 'กรุงเทพมหานคร' });
    expect(p.label).toBe('ตำแหน่งปัจจุบัน (GPS) · ใกล้ จ.กรุงเทพมหานคร');
    expect(p.notice).toBeNull();
  });

  it('GPS: a recent cached fix is used without waiting for a new one', async () => {
    L.getLastKnownPositionAsync.mockResolvedValueOnce({
      coords: { latitude: 18.7883, longitude: 98.9853 },
    } as never);
    const p = await resolvePlace(settings({ locationMode: 'gps' }));
    expect(p.province).toBe('เชียงใหม่');
    expect(L.getCurrentPositionAsync).not.toHaveBeenCalled();
  });

  it('GPS permission denied: falls back to the last province (or Pathum Thani) and says why', async () => {
    L.getForegroundPermissionsAsync.mockResolvedValue({ status: 'denied' } as never);
    const withProv = await resolvePlace(settings({ locationMode: 'gps', province: 'นนทบุรี' }));
    expect(withProv).toMatchObject({ source: 'province', province: 'นนทบุรี' });
    expect(withProv.label).toBe('จ.นนทบุรี (จากตำแหน่งล่าสุด)');
    expect(withProv.notice).toMatch(/ไม่ได้รับสิทธิ์ตำแหน่ง จึงใช้จ\.นนทบุรีแทน/);
    const none = await resolvePlace(settings({ locationMode: 'gps' }));
    expect(none).toMatchObject({ source: 'default', lat: 14.02, lon: 100.52 });
    expect(none.notice).toMatch(/จึงใช้ปทุมธานีแทน/);
    expect(L.getCurrentPositionAsync).not.toHaveBeenCalled();
  });

  it('GPS: no fix within the timeout falls back with a notice', async () => {
    jest.useFakeTimers();
    try {
      L.getCurrentPositionAsync.mockReturnValueOnce(new Promise(() => {}) as never);
      const pending = resolvePlace(settings({ locationMode: 'gps' }));
      await jest.advanceTimersByTimeAsync(LOCATION_TIMEOUT_MS + 1);
      const p = await pending;
      expect(p.source).toBe('default');
      expect(p.notice).toMatch(/หาตำแหน่งปัจจุบันไม่ได้/);
    } finally {
      jest.useRealTimers();
    }
  });

  it('fallbackPlace ignores a province that is not in the table', () => {
    const p = fallbackPlace(settings({ locationMode: 'province', province: 'x' }), null);
    expect(p.source).toBe('default');
  });
});
