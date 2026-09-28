import { useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { HourUV } from '@/api/types';
import { Card, colors } from '@/components/Card';
import {
  hourTick,
  initialFocusIndex,
  LEVEL_GRIDLINES,
  peakIndex,
  scaleY,
  scrollOffsetFor,
  yMax,
} from '@/lib/chart';
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
 * range as a thin whisker. Tap a column to read that hour (phones have no hover); the chosen
 * hour is marked by a dot under the axis, not a tall background that could read as a value.
 * At night the chart opens on the next day's peak hour instead of the dark hours.
 */
export function HourlyChart({ hours, isDaylight }: { hours: HourUV[]; isDaylight: boolean }) {
  const [selected, setSelected] = useState(() => initialFocusIndex(hours, isDaylight));
  const scroll = useRef<ScrollView>(null);
  const scrolled = useRef(false);
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
        {selected === 0 ? 'ตอนนี้ ' : sel.time.slice(0, 10) !== hours[0].time.slice(0, 10) ? 'พรุ่งนี้ ' : ''}
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
        <ScrollView
          ref={scroll}
          horizontal
          showsHorizontalScrollIndicator={false}
          testID="chart-scroll"
          onLayout={(e) => {
            // first layout only: centre the focused hour (daytime now, or tomorrow's peak)
            if (scrolled.current) return;
            scrolled.current = true;
            const x = scrollOffsetFor(selected, SLOT_W, e.nativeEvent.layout.width, hours.length);
            if (x > 0) scroll.current?.scrollTo({ x, animated: false });
          }}>
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
                      style={styles.slot}
                      accessibilityRole="button"
                      accessibilityState={{ selected: i === selected }}
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
                          testID={`bar-fill-${i}`}
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
                <View key={h.time} style={styles.tickSlot}>
                  <View
                    style={[styles.marker, i === selected && styles.markerOn]}
                    testID={i === selected ? 'selected-marker' : undefined}
                  />
                  <Text style={[styles.hour, i === selected && styles.hourOn]}>
                    {i === selected ? h.time.slice(11, 13) : (hourTick(h.time, i) ?? '')}
                  </Text>
                </View>
              ))}
            </View>
          </View>
        </ScrollView>
      </View>

      <Text style={styles.summary} testID="chart-summary">
        สูงสุด {hours[peak].uvi.toFixed(1)} ({hours[peak].level}) เวลา {formatClock(hours[peak].time)} ·
        แท่งคือค่าประมาณ เส้นคือช่วง q10–q90 · แตะแท่งเพื่อดูรายละเอียด (จุดใต้แกนคือชั่วโมงที่เลือก)
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
  },
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
  tickSlot: { width: SLOT_W, alignItems: 'center', gap: 2, paddingTop: 3 },
  marker: { width: 8, height: 8, borderRadius: 4 },
  markerOn: { backgroundColor: colors.text },
  hourOn: { color: colors.text, fontWeight: '700' },
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
