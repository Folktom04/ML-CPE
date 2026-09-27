import { StyleSheet, Text, View } from 'react-native';

import type { PredictResponse } from '@/api/types';
import { formatBurn } from '@/lib/uv';

import { Card, colors } from './Card';

/** UVA / UVB irradiance, burn time for the user's skin type and SPF/PA advice. */
export function UvaUvbCard({ data }: { data: PredictResponse }) {
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

      {data.advice.length > 0 ? (
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
});
