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

import { Card, Note, colors } from './Card';

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
    <Card
      title={
        stale
          ? `ดัชนี UV ช่วง ${formatHourInterval(data.time)} น. (ยังไม่ได้อัปเดตเป็นชั่วโมงปัจจุบัน)`
          : `ดัชนี UV ตอนนี้ (${formatHourInterval(data.time)} น.)`
      }>
      <View style={styles.row}>
        <Text style={[styles.uvi, { color }]} testID="uvi-value">
          {data.uvi.toFixed(1)}
        </Text>
        <View style={[styles.badge, { backgroundColor: color }]} testID="level-badge">
          <Text style={[styles.badgeText, { color: textOn(color) }]}>{data.level}</Text>
        </View>
      </View>
      <Text style={styles.muted}>
        ช่วงที่น่าจะเป็น (q10–q90): {formatRange(data.uvi_range)}
      </Text>

      {showAlert ? (
        <View style={[styles.alert, { backgroundColor: alertColor }]} testID="alert-strip">
          <Text style={[styles.alertText, { color: textOn(alertColor) }]}>
            เตือนตามค่าบน (q90) {data.alert_uvi.toFixed(1)}: ระดับ{data.alert_level}
          </Text>
        </View>
      ) : null}

      <Text style={styles.body} testID="next-safe">
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
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  uvi: { fontSize: 64, fontWeight: '700', lineHeight: 72 },
  badge: { borderRadius: 999, paddingHorizontal: 14, paddingVertical: 6 },
  badgeText: { fontSize: 18, fontWeight: '700' },
  muted: { color: colors.muted, fontSize: 14 },
  body: { color: colors.text, fontSize: 15 },
  alert: { borderRadius: 10, paddingHorizontal: 12, paddingVertical: 8 },
  alertText: { fontSize: 15, fontWeight: '600' },
});
