import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { HourUV } from '@/api/types';
import { Card, colors, ui } from '@/components/Card';
import { clockBkk } from '@/components/SunSessionCard';
import {
  ACTIVITIES,
  DURATIONS,
  planActivity,
  RISK_COLORS,
  riskAdvice,
  riskOf,
  type Slot,
} from '@/lib/planner';
import type { SkinType } from '@/lib/skinQuiz';
import { NOW_INTERVAL_MS, useNow } from '@/lib/useNow';

/** Bangkok calendar day of a time in ms, e.g. "2026-11-07". */
function dayBkk(ms: number): string {
  return new Date(ms + 7 * 3600 * 1000).toISOString().slice(0, 10);
}

function Chip({
  label,
  selected,
  onPress,
  testID,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
  testID: string;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[ui.seg, selected && ui.segOn]}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      testID={testID}>
      <Text style={[ui.segText, selected && ui.segTextOn]}>{label}</Text>
    </Pressable>
  );
}

function SlotRow({
  slot,
  nowMs,
  label,
  testID,
}: {
  slot: Slot;
  nowMs: number;
  label?: string;
  testID: string;
}) {
  const risk = riskOf(slot.fraction);
  const color = RISK_COLORS[risk];
  const pct = Math.round(slot.fraction * 100);
  const tomorrow = dayBkk(slot.startMs) !== dayBkk(nowMs) ? 'พรุ่งนี้ ' : '';
  return (
    <View style={styles.slot} testID={testID}>
      <View style={[styles.bar, { backgroundColor: color }]} />
      <View style={styles.slotBody}>
        <Text style={styles.slotTime}>
          {label ?? `${tomorrow}${clockBkk(slot.startMs)}–${clockBkk(slot.endMs)}`}
        </Text>
        <Text style={styles.text}>
          ได้รับ UV ประมาณ <Text style={[styles.pct, { color }]}>{pct} %</Text> ของปริมาณที่ทำให้ผิวแดง
        </Text>
        <Text style={styles.hint}>{riskAdvice(risk)}</Text>
      </View>
    </View>
  );
}

/**
 * "Plan an outdoor activity": pick an activity and a length, see the start times in the
 * forecast with the smallest UV dose for the user's skin type, the one to avoid, and "now".
 */
export function PlannerCard({
  hours,
  skin,
  nowMs: fixedNow,
}: {
  hours: HourUV[];
  skin: SkinType;
  /** Fixed clock for tests; the app uses `useNow`. */
  nowMs?: number;
}) {
  const nowMs = useNow(NOW_INTERVAL_MS, fixedNow);
  const [activityKey, setActivityKey] = useState(ACTIVITIES[0].key);
  const [minutes, setMinutes] = useState(ACTIVITIES[0].minutes);
  const activity = ACTIVITIES.find((a) => a.key === activityKey) ?? ACTIVITIES[0];
  // re-plan per 30-minute grid step, not on every 30 s tick
  const step = Math.floor(nowMs / (30 * 60 * 1000));
  const plan = useMemo(
    () => planActivity(hours, skin, minutes, nowMs),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [hours, skin, minutes, step],
  );

  const showWorst =
    plan.worst !== null && !plan.best.some((b) => b.startMs === plan.worst!.startMs);

  return (
    <Card title="วางแผนกิจกรรมกลางแจ้ง">
      <View style={ui.segTrack}>
        {ACTIVITIES.map((a) => (
          <Chip
            key={a.key}
            label={a.label}
            selected={a.key === activityKey}
            onPress={() => {
              setActivityKey(a.key);
              setMinutes(a.minutes);
            }}
            testID={`plan-activity-${a.key}`}
          />
        ))}
      </View>
      <View style={ui.segTrack}>
        {DURATIONS.map((m) => (
          <Chip
            key={m}
            label={m < 60 ? `${m} นาที` : `${m / 60} ชม.`}
            selected={m === minutes}
            onPress={() => setMinutes(m)}
            testID={`plan-minutes-${m}`}
          />
        ))}
      </View>

      {plan.best.length === 0 ? (
        <Text style={styles.text} testID="plan-empty">
          ช่วงพยากรณ์ที่เหลือไม่มีแดดยาวพอสำหรับ {minutes} นาที ลองลดเวลาหรือดูใหม่พรุ่งนี้เช้า
        </Text>
      ) : (
        <>
          <Text style={styles.section}>ช่วงที่โดนแดดน้อยที่สุด (ผิวประเภท {skin})</Text>
          {plan.best.map((s, i) => (
            <SlotRow key={s.startMs} slot={s} nowMs={nowMs} testID={`plan-best-${i}`} />
          ))}
          {showWorst ? (
            <>
              <Text style={styles.section}>ช่วงที่ควรเลี่ยง</Text>
              <SlotRow slot={plan.worst!} nowMs={nowMs} testID="plan-worst" />
            </>
          ) : null}
        </>
      )}

      {plan.now ? (
        <>
          <Text style={styles.section}>ถ้าออกไปตอนนี้</Text>
          <SlotRow
            slot={plan.now}
            nowMs={nowMs}
            label={`ตอนนี้–${clockBkk(plan.now.endMs)}`}
            testID="plan-now"
          />
        </>
      ) : null}

      {activity.hint ? (
        <Text style={styles.hint} testID="plan-activity-hint">
          {activity.hint}
        </Text>
      ) : null}
      <Text style={styles.hint}>
        คิดจากค่าบนของ UV (q90) และอยู่กลางแดดตลอดกิจกรรม เหมือนการ์ด “อยู่กลางแจ้ง”
        ยังไม่ได้คิดร่มเงา เสื้อผ้า หรือครีมกันแดด
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  section: { ...ui.eyebrow, marginTop: 6 },
  slot: { flexDirection: 'row', gap: 12, backgroundColor: colors.background, borderRadius: 14, padding: 12 },
  bar: { width: 4, borderRadius: 2 },
  slotBody: { flex: 1, gap: 2 },
  slotTime: { color: colors.text, fontSize: 17, fontWeight: '700' },
  pct: { fontWeight: '700' },
  text: { color: colors.text, fontSize: 14 },
  hint: { color: colors.muted, fontSize: 12, lineHeight: 17 },
});
