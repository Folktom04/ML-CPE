import { useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import type { HourUV } from '@/api/types';
import { Card, colors, ui } from '@/components/Card';
import {
  peakAlertUvi,
  productUrl,
  recommendProducts,
  STORE_LABELS,
  type Product,
  type Store,
} from '@/lib/products';
import { levelIndex, WHO_LEVELS } from '@/lib/uv';

const STORES: Store[] = ['shopee', 'lazada'];

/**
 * "Sun-protection helpers": product tiles picked by the forecast peak. Tapping a picture shows
 * the store choice; a store button opens that store's app or website with `Linking`.
 */
export function ProductsCard({ hours }: { hours: HourUV[] }) {
  const [open, setOpen] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const peak = peakAlertUvi(hours);
  const products = recommendProducts(peak);

  const go = async (p: Product, store: Store) => {
    setFailed(false);
    try {
      await Linking.openURL(productUrl(p, store));
    } catch {
      setFailed(true);
    }
  };

  return (
    <Card title="ตัวช่วยกันแดด">
      <Text style={ui.hint} testID="products-reason">
        {peak > 0
          ? `ช่วงพยากรณ์นี้ UV สูงสุดประมาณ ${peak.toFixed(1)} (${WHO_LEVELS[levelIndex(peak)]}) · แตะรูปเพื่อเลือกร้านค้า`
          : 'แตะรูปเพื่อเลือกร้านค้า'}
      </Text>
      <View style={styles.grid}>
        {products.map((p) => {
          const isOpen = open === p.key;
          return (
            <View key={p.key} style={styles.tile} testID={`product-${p.key}`}>
              <Pressable
                onPress={() => setOpen(isOpen ? null : p.key)}
                accessibilityRole="button"
                accessibilityLabel={`${p.label} เลือกร้านค้า`}
                testID={`product-image-${p.key}`}
                style={[styles.image, { backgroundColor: p.tint }]}>
                <Text style={styles.icon}>{p.icon}</Text>
                <View style={styles.cart}>
                  <Text style={styles.cartText}>🛒</Text>
                </View>
              </Pressable>
              <Text style={styles.label}>{p.label}</Text>
              <Text style={styles.detail}>{p.detail}</Text>
              {isOpen ? (
                <View style={styles.stores} testID={`product-stores-${p.key}`}>
                  {STORES.map((s) => (
                    <Pressable
                      key={s}
                      onPress={() => go(p, s)}
                      accessibilityRole="link"
                      testID={`product-${p.key}-${s}`}
                      style={[styles.store, s === 'shopee' ? styles.shopee : styles.lazada]}>
                      <Text style={styles.storeText}>{STORE_LABELS[s]}</Text>
                    </Pressable>
                  ))}
                </View>
              ) : null}
            </View>
          );
        })}
      </View>
      {failed ? (
        <Text style={styles.error} testID="products-error">
          เปิดร้านค้าไม่สำเร็จ ลองใหม่อีกครั้ง
        </Text>
      ) : null}
      <Text style={ui.hint}>
        ลิงก์ไปยังร้านค้าภายนอก แอปไม่ได้ขายสินค้าเอง ตรวจสอบเลข อย. ส่วนผสม และรีวิวก่อนซื้อ
        ครีมกันแดดควรทาซ้ำทุก 2 ชม. และหลังว่ายน้ำหรือเหงื่อออก
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  tile: { width: '47%', flexGrow: 1, gap: 4 },
  image: {
    aspectRatio: 1,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  icon: { fontSize: 56 },
  cart: {
    position: 'absolute',
    right: 8,
    bottom: 8,
    backgroundColor: colors.card,
    borderRadius: 980,
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 1px 4px rgba(0,0,0,0.15)',
  },
  cartText: { fontSize: 16 },
  label: { color: colors.text, fontSize: 15, fontWeight: '700' },
  detail: { color: colors.muted, fontSize: 12, lineHeight: 17 },
  stores: { flexDirection: 'row', gap: 6, marginTop: 4 },
  store: { flex: 1, borderRadius: 980, paddingVertical: 8, alignItems: 'center' },
  shopee: { backgroundColor: '#EE4D2D' },
  lazada: { backgroundColor: '#0F146D' },
  storeText: { color: '#FFFFFF', fontSize: 13, fontWeight: '700' },
  error: { color: '#D70015', fontSize: 13 },
});
