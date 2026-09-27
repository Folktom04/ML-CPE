import { StyleSheet, Text, View } from 'react-native';

import type { PredictResponse } from '@/api/types';
import { formatBurn, formatClock, formatRange, levelColor, textOn, type DayPeak } from '@/lib/uv';

import { Card, colors } from './Card';

/**
 * UVA / UVB irradiance, burn time for the user's skin type and SPF/PA advice.
 * At night the advice is hidden (it would say e.g. "wear sunglasses" at UVI 0) and the
 * peak of the next daytime period from /forecast is shown instead (`nextPeak`).
 */
export function UvaUvbCard({
  data,
  nextPeak = null,
}: {
  data: PredictResponse;
  nextPeak?: DayPeak | null;
}) {
  return (
    <Card title="UVA / UVB และเวลาผิวไหม้">
      <View style={styles.row}>
        <View style={styles.cell}>
          <Text style={styles.label}>UVA</Text>
          <Text style={styles.value} testID="uva-value">
            {data.uva_wm2.toFixed(1)} <Text style={styles.unit}>W/m²</Text>
          </Text>
          <Text style={styles.hint}>ทำให้ผิวแก่ก่อนวัย ผ่านเมฆและกระจกได้</Text>
        </View>
        <View style={styles.cell}>
          <Text style={styles.label}>UVB</Text>
          <Text style={styles.value} testID="uvb-value">
            {data.uvb_wm2.toFixed(2)} <Text style={styles.unit}>W/m²</Text>
          </Text>
          <Text style={styles.hint}>ทำให้ผิวไหม้แดด</Text>
        </View>
      </View>

      <View style={styles.burn}>
        <Text style={styles.label}>ผิวประเภท {data.skin_type}: เวลาก่อนผิวไหม้</Text>
        <Text style={styles.burnValue} testID="burn-value">
          {formatBurn(data.burn_minutes, data.is_daylight)}
        </Text>
        <Text style={styles.hint}>คิดจากค่า UV ด้านบนของช่วง (q90) เพื่อความปลอดภัย</Text>
      </View>

      {!data.is_daylight ? (
        <NextPeak peak={nextPeak} />
      ) : data.advice.length > 0 ? (
        <View style={styles.advice}>
          {data.advice.map((a) => (
            <Text key={a} style={styles.adviceItem}>
              • {a}
            </Text>
          ))}
        </View>
      ) : null}
    </Card>
  );
}

/** Night view: highest forecast UVI of the next daytime period. */
function NextPeak({ peak }: { peak: DayPeak | null }) {
  if (!peak) {
    return (
      <Text style={styles.hint} testID="next-peak">
        ยังไม่มีข้อมูลพยากรณ์ของวันถัดไป
      </Text>
    );
  }
  const color = levelColor(peak.level, peak.uvi);
  return (
    <View style={styles.peak} testID="next-peak">
      <Text style={styles.label}>{peak.isTomorrow ? 'พรุ่งนี้' : 'วันนี้'} UV สูงสุดประมาณ</Text>
      <View style={styles.peakRow}>
        <Text style={styles.value}>{peak.uvi.toFixed(1)}</Text>
        <View style={[styles.peakBadge, { backgroundColor: color }]} testID="next-peak-badge">
          <Text style={{ color: textOn(color), fontWeight: '700' }}>{peak.level}</Text>
        </View>
        <Text style={styles.label}>ราว {formatClock(peak.time)} น.</Text>
      </View>
      <Text style={styles.hint}>ช่วงที่น่าจะเป็น {formatRange(peak.uvi_range)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 12 },
  cell: { flex: 1, gap: 2 },
  label: { color: colors.muted, fontSize: 14 },
  value: { color: colors.text, fontSize: 26, fontWeight: '700' },
  unit: { fontSize: 14, fontWeight: '400', color: colors.muted },
  hint: { color: colors.muted, fontSize: 12 },
  burn: { borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 10, gap: 2 },
  burnValue: { color: colors.text, fontSize: 28, fontWeight: '700' },
  advice: { gap: 4, paddingTop: 4 },
  adviceItem: { color: colors.text, fontSize: 14 },
  peak: { gap: 4, paddingTop: 4 },
  peakRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  peakBadge: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3 },
});
