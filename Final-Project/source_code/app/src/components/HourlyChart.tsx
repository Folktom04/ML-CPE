import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { HourUV } from '@/api/types';
import { Card, colors } from '@/components/Card';
import { hourTick, LEVEL_GRIDLINES, peakIndex, scaleY, yMax } from '@/lib/chart';
import {
  formatClock,
  formatHourInterval,
  formatRange,
  levelColor,
  WHO_COLORS,
  WHO_LEVELS,
} from '@/lib/uv';

const PLOT_H = 140;
const SLOT_W = 26; // bar 14 px + air; bars never touch
const BAR_W = 14;
const AXIS_W = 24;
const LABEL_H = 16;

/**
 * Hourly UV forecast (now + next 24 h) as columns in the WHO level colours, with the q10–q90
 * range as a thin whisker. Tap a column to read that hour (phones have no hover).
 */
export function HourlyChart({ hours }: { hours: HourUV[] }) {
  const [selected, setSelected] = useState(0);
  if (hours.length === 0) {
    return (
      <Card title="พยากรณ์รายชั่วโมง">
        <Text style={styles.muted}>ยังไม่มีข้อมูลพยากรณ์</Text>
      </Card>
    );
  }
  const max = yMax(hours);
  const peak = peakIndex(hours);
  const sel = hours[Math.min(selected, hours.length - 1)];
  const top = PLOT_H + LABEL_H; // room for the peak label above the tallest column

  return (
    <Card title="พยากรณ์รายชั่วโมง (UVI)">
      <Text style={styles.detail} testID="chart-detail">
        {selected === 0 ? 'ตอนนี้ ' : ''}
        {formatHourInterval(sel.time)} · UVI {sel.uvi.toFixed(1)} ({formatRange(sel.uvi_range)}) ·{' '}
        {sel.level}
        {sel.data_imputed ? ' · ข้อมูลบางส่วนถูกเติม' : ''}
      </Text>

      <View style={styles.row}>
        <View style={[styles.axis, { height: top }]}>
          {LEVEL_GRIDLINES.filter((g) => g <= max).map((g) => (
            <Text
              key={g}
              style={[styles.tick, { bottom: scaleY(g, max, PLOT_H) - 7 }]}
              testID={`grid-${g}`}>
              {g}
            </Text>
          ))}
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} testID="chart-scroll">
          <View>
            <View style={{ height: top, width: SLOT_W * hours.length }}>
              {LEVEL_GRIDLINES.filter((g) => g <= max).map((g) => (
                <View key={g} style={[styles.grid, { bottom: scaleY(g, max, PLOT_H) }]} />
              ))}
              <View style={styles.columns}>
                {hours.map((h, i) => {
                  const barH = scaleY(h.uvi, max, PLOT_H);
                  const lo = scaleY(h.uvi_range[0], max, PLOT_H);
                  const hi = scaleY(h.uvi_range[1], max, PLOT_H);
                  return (
                    <Pressable
                      key={h.time}
                      onPress={() => setSelected(i)}
                      style={[styles.slot, i === selected && styles.slotSelected]}
                      accessibilityRole="button"
                      accessibilityLabel={`${formatHourInterval(h.time)} UVI ${h.uvi.toFixed(1)} ระดับ${h.level}`}
                      testID={`bar-${i}`}>
                      {i === peak && h.uvi > 0 ? (
                        <Text style={[styles.peak, { bottom: Math.max(barH, hi) + 2 }]} testID="peak-label">
                          {h.uvi.toFixed(1)}
                        </Text>
                      ) : null}
                      {barH > 0 ? (
                        <View
                          style={[
                            styles.bar,
                            { height: barH, backgroundColor: levelColor(h.level, h.uvi) },
                          ]}
                        />
                      ) : (
                        <View style={styles.zero} />
                      )}
                      {hi - lo > 1 ? (
                        <View style={[styles.whisker, { bottom: lo, height: hi - lo }]} />
                      ) : null}
                    </Pressable>
                  );
                })}
              </View>
            </View>
            <View style={styles.baseline} />
            <View style={styles.ticks}>
              {hours.map((h, i) => (
                <Text key={h.time} style={styles.hour}>
                  {hourTick(h.time, i) ?? ''}
                </Text>
              ))}
            </View>
          </View>
        </ScrollView>
      </View>

      <Text style={styles.summary} testID="chart-summary">
        สูงสุด {hours[peak].uvi.toFixed(1)} ({hours[peak].level}) เวลา {formatClock(hours[peak].time)} ·
        แท่งคือค่าประมาณ เส้นคือช่วง q10–q90 · แตะแท่งเพื่อดูรายละเอียด
      </Text>
      <View style={styles.legend}>
        {WHO_LEVELS.map((name, i) => (
          <View key={name} style={styles.legendItem}>
            <View style={[styles.swatch, { backgroundColor: WHO_COLORS[i] }]} />
            <Text style={styles.legendText}>{name}</Text>
          </View>
        ))}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  muted: { color: colors.muted },
  detail: { color: colors.text, fontSize: 14, fontWeight: '600' },
  row: { flexDirection: 'row' },
  axis: { width: AXIS_W, position: 'relative' },
  tick: {
    position: 'absolute',
    right: 4,
    fontSize: 10,
    color: colors.muted,
    fontVariant: ['tabular-nums'],
  },
  grid: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.border,
  },
  columns: { position: 'absolute', left: 0, right: 0, bottom: 0, top: 0, flexDirection: 'row' },
  slot: {
    width: SLOT_W,
    height: '100%',
    alignItems: 'center',
    justifyContent: 'flex-end',
    borderRadius: 6,
  },
  slotSelected: { backgroundColor: '#E9EEF4' },
  bar: { width: BAR_W, borderTopLeftRadius: 4, borderTopRightRadius: 4 },
  zero: { width: BAR_W, height: 2, backgroundColor: colors.border },
  whisker: {
    position: 'absolute',
    width: 2,
    backgroundColor: colors.text,
    opacity: 0.55,
    borderRadius: 1,
  },
  peak: {
    position: 'absolute',
    fontSize: 11,
    fontWeight: '600',
    color: colors.text,
    width: SLOT_W + 12,
    textAlign: 'center',
  },
  baseline: { height: 1, backgroundColor: colors.muted, opacity: 0.4 },
  ticks: { flexDirection: 'row' },
  hour: {
    width: SLOT_W,
    textAlign: 'center',
    fontSize: 10,
    color: colors.muted,
    fontVariant: ['tabular-nums'],
  },
  summary: { color: colors.muted, fontSize: 12 },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  swatch: { width: 10, height: 10, borderRadius: 2 },
  legendText: { fontSize: 12, color: colors.muted },
});
