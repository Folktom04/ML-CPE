/**
 * Where to compute UV for (day 21): GPS, a province picked by hand, or the default.
 *
 * - GPS needs foreground ("while using the app") permission only. The fix is rounded to 0.01°
 *   (~1 km) before it is sent to /predict and is never stored on the phone; only the name of the
 *   nearest province is kept (and sent to the server only with consent).
 * - Permission denied, GPS off or no fix within LOCATION_TIMEOUT_MS: the chosen province is
 *   used, else Pathum Thani, and the screen says why.
 */

import * as Location from 'expo-location';

import { DEFAULT_LOCATION } from '@/config';
import { findProvince, nearestProvince } from '@/lib/provinces';
import type { Settings } from '@/lib/settings';

export const LOCATION_TIMEOUT_MS = 10000;
/** A cached fix younger than this is good enough (UV does not change over a few km). */
export const LAST_KNOWN_MAX_AGE_MS = 15 * 60 * 1000;

export type Place = {
  lat: number;
  lon: number;
  /** What the home screen shows, e.g. "ตำแหน่งปัจจุบัน (GPS) · ใกล้ จ.นนทบุรี". */
  label: string;
  source: 'gps' | 'province' | 'default';
  /** Nearest (GPS) or chosen province, Thai name. */
  province: string | null;
  /** Why the wanted source could not be used (permission denied, no fix), or null. */
  notice: string | null;
};

/** Round a coordinate to 0.01° (about 1 km), as the API cache and the database do. */
export function roundCoord(x: number): number {
  return Math.round(x * 100) / 100;
}

/** Ask for "while using the app" location permission; true when granted. */
export async function requestLocationPermission(): Promise<boolean> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    return status === 'granted';
  } catch {
    return false;
  }
}

function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`no location fix within ${ms / 1000} s`)), ms);
    p.then(
      (v) => {
        clearTimeout(t);
        resolve(v);
      },
      (e) => {
        clearTimeout(t);
        reject(e);
      },
    );
  });
}

/** Chosen province, else the default place, with an optional notice. */
export function fallbackPlace(s: Settings, notice: string | null): Place {
  const p = findProvince(s.province);
  if (p && s.locationMode !== null) {
    return {
      lat: p.lat,
      lon: p.lon,
      label: `จ.${p.name_th} (${s.locationMode === 'province' ? 'เลือกเอง' : 'จากตำแหน่งล่าสุด'})`,
      source: 'province',
      province: p.name_th,
      notice,
    };
  }
  return {
    lat: DEFAULT_LOCATION.lat,
    lon: DEFAULT_LOCATION.lon,
    label: `${DEFAULT_LOCATION.name} (ตำแหน่งเริ่มต้น)`,
    source: 'default',
    province: null,
    notice,
  };
}

/** The place to compute UV for, following the user's setting and falling back safely. */
export async function resolvePlace(s: Settings): Promise<Place> {
  if (s.locationMode !== 'gps') return fallbackPlace(s, null);
  const where = s.province ? `จ.${s.province}` : DEFAULT_LOCATION.name;
  try {
    const perm = await Location.getForegroundPermissionsAsync();
    if (perm.status !== 'granted') {
      return fallbackPlace(
        s,
        `ไม่ได้รับสิทธิ์ตำแหน่ง จึงใช้${where}แทน เปลี่ยนได้ในหน้าตั้งค่า`,
      );
    }
    const pos =
      (await Location.getLastKnownPositionAsync({ maxAge: LAST_KNOWN_MAX_AGE_MS })) ??
      (await withTimeout(
        Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }),
        LOCATION_TIMEOUT_MS,
      ));
    const lat = roundCoord(pos.coords.latitude);
    const lon = roundCoord(pos.coords.longitude);
    const near = nearestProvince(lat, lon);
    return {
      lat,
      lon,
      label: `ตำแหน่งปัจจุบัน (GPS) · ใกล้ จ.${near.name_th}`,
      source: 'gps',
      province: near.name_th,
      notice: null,
    };
  } catch {
    return fallbackPlace(s, `หาตำแหน่งปัจจุบันไม่ได้ (เปิด GPS หรือยัง?) จึงใช้${where}แทน`);
  }
}
