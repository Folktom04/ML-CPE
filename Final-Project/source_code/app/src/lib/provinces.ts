/**
 * Thailand's 77 provinces with the capital's coordinates (day 21), for the "pick a province"
 * fallback when location permission is denied. Built by `source_code/src/provinces.py` from the
 * Open-Meteo Geocoding API (GeoNames, CC BY 4.0; see docs/datasets.md).
 */

import table from '@/data/provinces.json';

export type Province = {
  name_th: string;
  name_en: string;
  lat: number;
  lon: number;
};

export const PROVINCES: Province[] = table.provinces.map(({ name_th, name_en, lat, lon }) => ({
  name_th,
  name_en,
  lat,
  lon,
}));

export const PROVINCE_SOURCE: string = table.source;

const BY_NAME = new Map(PROVINCES.map((p) => [p.name_th, p]));

export function isProvinceName(v: unknown): v is string {
  return typeof v === 'string' && BY_NAME.has(v);
}

export function findProvince(nameTh: string | null): Province | null {
  return nameTh ? (BY_NAME.get(nameTh) ?? null) : null;
}

/** Great-circle distance in km (same formula as `distance_km` in src/inference.py). */
export function distanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const rad = Math.PI / 180;
  const dp = (lat2 - lat1) * rad;
  const dl = (lon2 - lon1) * rad;
  const a =
    Math.sin(dp / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dl / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(a));
}

/**
 * Province whose capital is nearest to a point. Near a border this can be the neighbouring
 * province; for UV (which changes slowly with distance) that is acceptable.
 */
export function nearestProvince(lat: number, lon: number): Province {
  let best = PROVINCES[0];
  let bestKm = Infinity;
  for (const p of PROVINCES) {
    const km = distanceKm(lat, lon, p.lat, p.lon);
    if (km < bestKm) {
      best = p;
      bestKm = km;
    }
  }
  return best;
}

/** Provinces whose Thai or English name contains `query` (case-insensitive, spaces ignored). */
export function searchProvinces(query: string): Province[] {
  const q = query.trim().toLowerCase().replace(/\s+/g, '');
  if (!q) return PROVINCES;
  return PROVINCES.filter(
    (p) =>
      p.name_th.replace(/\s+/g, '').includes(q) ||
      p.name_en.toLowerCase().replace(/\s+/g, '').includes(q),
  );
}
