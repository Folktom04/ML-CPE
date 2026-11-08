import { StyleSheet, Text, View } from 'react-native';

import type { PredictResponse } from '@/api/types';
import {
  alertIsHigher,
  formatClock,
  formatHourInterval,
  formatRange,
  levelColor,
  levelIndexOf,
  textOn,
} from '@/lib/uv';

import { Note, ui } from './Card';

/**
 * UV now: point UVI, q10–q90 range, WHO level colour and the upper-quantile warning. With
 * `stale` (the clock hour has moved on and the data could not be updated yet) the title names
 * the hour of the data without "ตอนนี้".
 */
export function UVCard({ data, stale = false }: { data: PredictResponse; stale?: boolean }) {
  const color = levelColor(data.level, data.uvi);
  const alertColor = levelColor(data.alert_level, data.alert_uvi);
  const showAlert = alertIsHigher(data.level, data.alert_level);
  const lowNow = levelIndexOf(data.alert_level) === 0;

  return (
    <View style={styles.heroBox}>
      <Text style={styles.tagline}>แดดตอนนี้แรงแค่ไหน</Text>
      <Text style={[ui.eyebrow, styles.center, styles.dim]}>
        {stale
          ? `ดัชนี UV ช่วง ${formatHourInterval(data.time)} น. (ยังไม่ได้อัปเดตเป็นชั่วโมงปัจจุบัน)`
          : `ดัชนี UV ตอนนี้ (${formatHourInterval(data.time)} น.)`}
      </Text>
      <View style={styles.hero}>
        <Text style={[styles.uvi, { color }]} testID="uvi-value">
          {data.uvi.toFixed(1)}
        </Text>
        <View style={[styles.badge, { backgroundColor: color }]} testID="level-badge">
          <Text style={[styles.badgeText, { color: textOn(color) }]}>{data.level}</Text>
        </View>
      </View>
      <Text style={[styles.muted, styles.center, styles.dim]}>
        ช่วงที่น่าจะเป็น (q10–q90): {formatRange(data.uvi_range)}
      </Text>

      {showAlert ? (
        <View style={[styles.alert, { backgroundColor: alertColor }]} testID="alert-strip">
          <Text style={[styles.alertText, { color: textOn(alertColor) }]}>
            เตือนตามค่าบน (q90) {data.alert_uvi.toFixed(1)}: ระดับ{data.alert_level}
          </Text>
        </View>
      ) : null}

      <Text style={[styles.body, styles.center]} testID="next-safe">
        {lowNow
          ? 'ตอนนี้ UV อยู่ในระดับต่ำ'
          : data.next_safe_time
            ? `UV กลับสู่ระดับต่ำประมาณ ${formatClock(data.next_safe_time)} น.`
            : 'UV ยังไม่กลับสู่ระดับต่ำในช่วงพยากรณ์'}
      </Text>

      {data.data_imputed ? (
        <Note testID="imputed-note">
          ข้อมูลสภาพอากาศบางส่วนของชั่วโมงนี้ถูกเติม ค่าอาจคลาดเคลื่อนมากขึ้น
        </Note>
      ) : null}
      {data.interval_adjusted ? <Note>ช่วงถูกขยายให้ครอบคลุมค่าที่แสดง</Note> : null}
      {data.note ? <Note>{data.note}</Note> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  // full-width black hero, like the top of an Apple product page
  heroBox: {
    backgroundColor: '#000000',
    marginHorizontal: -16,
    paddingHorizontal: 24,
    paddingTop: 36,
    paddingBottom: 32,
    gap: 12,
  },
  tagline: {
    color: '#F5F5F7',
    fontSize: 34,
    lineHeight: 42,
    fontWeight: '800',
    letterSpacing: -0.8,
    textAlign: 'center',
  },
  center: { textAlign: 'center' },
  dim: { color: '#A1A1A6' },
  hero: { alignItems: 'center', gap: 12, paddingVertical: 6 },
  uvi: { fontSize: 128, fontWeight: '800', lineHeight: 136, letterSpacing: -5 },
  badge: { borderRadius: 980, paddingHorizontal: 20, paddingVertical: 7 },
  badgeText: { fontSize: 18, fontWeight: '700' },
  muted: { fontSize: 15 },
  body: { color: '#F5F5F7', fontSize: 19, fontWeight: '600' },
  alert: { borderRadius: 980, paddingHorizontal: 18, paddingVertical: 10, alignSelf: 'center' },
  alertText: { fontSize: 15, fontWeight: '700', textAlign: 'center' },
});
