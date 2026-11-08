/**
 * Sun-protection product suggestions with links to Shopee / Lazada.
 *
 * The app does not sell anything: a tap opens the store app (or its website when the app is not
 * installed). Links default to a store search for the product type; replace them in
 * `PRODUCT_LINKS` with links to specific products. Which items are shown depends on the highest
 * UV of the forecast (alert_uvi, the upper value, as for every warning).
 */

import type { HourUV } from '@/api/types';
import { roundUvi } from '@/lib/uv';

export type Store = 'shopee' | 'lazada';

export const STORE_LABELS: Record<Store, string> = { shopee: 'Shopee', lazada: 'Lazada' };

/** Store search page for a keyword (used until a specific product link is set). */
export function searchUrl(store: Store, keyword: string): string {
  const q = encodeURIComponent(keyword);
  return store === 'shopee'
    ? `https://shopee.co.th/search?keyword=${q}`
    : `https://www.lazada.co.th/catalog/?q=${q}`;
}

export type Product = {
  key: string;
  label: string;
  detail: string;
  /** Picture of the tile (drawn icon, no brand images). */
  icon: string;
  /** Tile background. */
  tint: string;
  /** Search keyword for the default links. */
  keyword: string;
};

export const PRODUCTS: Product[] = [
  {
    key: 'spf50',
    label: 'ครีมกันแดด SPF50+ PA++++',
    detail: 'สำหรับวันที่ UV สูง ทาก่อนออกแดด 15 นาที',
    icon: '🧴',
    tint: '#FFF1D6',
    keyword: 'ครีมกันแดด SPF50 PA++++',
  },
  {
    key: 'spf30',
    label: 'ครีมกันแดด SPF30+',
    detail: 'ใช้ทุกวัน แม้วันที่ UV ไม่สูง',
    icon: '🧴',
    tint: '#E8F5EA',
    keyword: 'ครีมกันแดด SPF30',
  },
  {
    key: 'water',
    label: 'กันแดดกันน้ำ/กันเหงื่อ',
    detail: 'ว่ายน้ำ ออกกำลังกาย ทาซ้ำหลังขึ้นจากน้ำ',
    icon: '🏊',
    tint: '#E3F0FF',
    keyword: 'กันแดดกันน้ำ water resistant',
  },
  {
    key: 'hat',
    label: 'หมวกปีกกว้าง',
    detail: 'บังหน้า หู และต้นคอ',
    icon: '👒',
    tint: '#F6EBDD',
    keyword: 'หมวกปีกกว้าง กันแดด',
  },
  {
    key: 'glasses',
    label: 'แว่นกันแดด UV400',
    detail: 'ป้องกันดวงตาจาก UVA และ UVB',
    icon: '🕶️',
    tint: '#ECECF1',
    keyword: 'แว่นกันแดด UV400',
  },
  {
    key: 'umbrella',
    label: 'ร่มกัน UV',
    detail: 'สร้างร่มเงาเองเวลาเดินกลางแดด',
    icon: '☂️',
    tint: '#F1E6FA',
    keyword: 'ร่มกันยูวี UPF50',
  },
  {
    key: 'shirt',
    label: 'เสื้อแขนยาว UPF50+',
    detail: 'กันแดดได้โดยไม่ต้องทาครีมซ้ำ',
    icon: '👕',
    tint: '#E6F4F1',
    keyword: 'เสื้อกันแดด UPF50',
  },
];

/**
 * Links per product and store. Put a specific product link here to replace the search page,
 * e.g. `spf50: { shopee: 'https://shopee.co.th/...' }`. Missing entries use `searchUrl`.
 */
export const PRODUCT_LINKS: Partial<Record<string, Partial<Record<Store, string>>>> = {};

/** Link that a tile opens in a store. */
export function productUrl(product: Product, store: Store): string {
  return PRODUCT_LINKS[product.key]?.[store] ?? searchUrl(store, product.keyword);
}

/** Highest alert_uvi (upper value) among the daylight hours, or 0 without daylight hours. */
export function peakAlertUvi(hours: HourUV[]): number {
  return hours.reduce((m, h) => (h.is_daylight ? Math.max(m, h.alert_uvi) : m), 0);
}

/**
 * Products for a forecast peak (WHO rounding): below 3 only everyday sunscreen and a hat;
 * from 3 (ปานกลาง) the full set; from 6 (สูง) SPF50+ instead of SPF30+.
 */
export function recommendProducts(peakUvi: number): Product[] {
  const level = roundUvi(peakUvi);
  const pick = (keys: string[]) =>
    keys.map((k) => PRODUCTS.find((p) => p.key === k)!).filter(Boolean);
  if (level < 3) return pick(['spf30', 'hat']);
  const cream = level >= 6 ? 'spf50' : 'spf30';
  return pick([cream, 'water', 'hat', 'glasses', 'umbrella', 'shirt']);
}
