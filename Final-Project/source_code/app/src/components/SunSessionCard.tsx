import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { HourUV } from '@/api/types';
import { Card, colors, Note } from '@/components/Card';
import { planReapply } from '@/lib/alertPlan';
import { BURN_FRACTION, sunStatus } from '@/lib/dose';
import { notificationPermission, supported } from '@/lib/notifications';
import { useSettings } from '@/lib/SettingsContext';
import type { SkinType } from '@/lib/skinQuiz';

/** "HH:MM" in Asia/Bangkok of a time in ms. */
export function clockBkk(ms: number): string {
  return new Date(ms + 7 * 3600 * 1000).toISOString().slice(11, 16);
}

function Button({
  label,
  onPress,
  testID,
  kind = 'primary',
}: {
  label: string;
  onPress: () => void;
  testID: string;
  kind?: 'primary' | 'outline';
}) {
  return (
    <Pressable
      onPress={onPress}
      style={kind === 'primary' ? styles.primary : styles.outline}
      accessibilityRole="button"
      testID={testID}>
      <Text style={kind === 'primary' ? styles.primaryText : styles.outlineText}>{label}</Text>
    </Pressable>
  );
}

/**
 * "Going out" (dose to 80 % of the MED, full sun assumed) and "sunscreen applied" (reapply in
 * 2 h). The reminders themselves are scheduled by `useLocalNotifications`.
 */
export function SunSessionCard({
  hours,
  skin,
  isDaylight,
  nowMs: fixedNow,
}: {
  hours: HourUV[];
  skin: SkinType;
  isDaylight: boolean;
  /** Fixed clock for tests; the app ticks every minute. */
  nowMs?: number;
}) {
  const { settings: s, update } = useSettings();
  const [tick, setTick] = useState(() => Date.now());
  useEffect(() => {
    if (fixedNow !== undefined) return;
    const id = setInterval(() => setTick(Date.now()), 60 * 1000);
    return () => clearInterval(id);
  }, [fixedNow]);
  const nowMs = fixedNow ?? tick;
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [reapplyReason, setReapplyReason] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    notificationPermission(false).then((ok) => {
      if (active) setAllowed(ok);
    });
    return () => {
      active = false;
    };
  }, []);

  const status = s.sunStartedAt ? sunStatus(hours, skin, s.sunStartedAt, nowMs) : null;
  const reapplyDue = s.reapplyAt && s.reapplyAt > nowMs ? s.reapplyAt : null;

  const goOut = async () => {
    if (allowed === false) setAllowed(await notificationPermission(true));
    await update({ sunStartedAt: fixedNow ?? Date.now() });
  };

  const applied = async () => {
    const { plan, reason } = planReapply(hours, fixedNow ?? Date.now());
    setReapplyReason(reason);
    if (allowed === false) setAllowed(await notificationPermission(true));
    await update({ reapplyAt: plan ? plan.at : null });
  };

  if (!isDaylight && !status && !reapplyDue) return null;

  return (
    <Card title="อยู่กลางแจ้ง">
      {supported && allowed === false ? (
        <Note testID="notify-not-allowed">
          ยังไม่ได้อนุญาตการแจ้งเตือน ปุ่มด้านล่างยังคำนวณให้ แต่จะไม่มีการแจ้งเตือนเด้งขึ้นมา
        </Note>
      ) : null}

      {status ? (
        <View style={styles.block} testID="sun-status">
          <Text style={styles.value}>อยู่กลางแดดตั้งแต่ {clockBkk(s.sunStartedAt!)}</Text>
          <Text style={styles.text}>
            {status.fractionNow === null
              ? 'ยังคำนวณปริมาณ UV ที่ได้รับไม่ได้'
              : `ได้รับ UV แล้วประมาณ ${Math.round(status.fractionNow * 100)} % ของปริมาณที่ทำให้ผิวแดง (MED)`}
          </Text>
          <Text style={styles.text} testID="sun-warn-at">
            {status.warnAt === null
              ? `ช่วงพยากรณ์ที่มีอยู่ ไม่ถึง ${Math.round(BURN_FRACTION * 100)} % จึงยังไม่ตั้งเตือน`
              : status.warnAt <= nowMs
                ? `ถึง ${Math.round(BURN_FRACTION * 100)} % แล้วโดยประมาณ ควรเข้าร่มหรือป้องกันผิว`
                : `จะเตือนราว ${clockBkk(status.warnAt)} (ที่ประมาณ ${Math.round(BURN_FRACTION * 100)} % ของ MED)`}
          </Text>
          <Button
            label="เข้าร่มแล้ว"
            kind="outline"
            onPress={() => update({ sunStartedAt: null })}
            testID="sun-stop"
          />
        </View>
      ) : isDaylight ? (
        <Button label="ออกแดด" onPress={goOut} testID="sun-start" />
      ) : null}
      <Text style={styles.hint} testID="sun-hint">
        คิดจากกรณีอยู่กลางแดดเต็มที่และใช้ค่าบนของ UV ถ้าอยู่ในร่มบ้าง เวลาจริงจะนานกว่านี้
        ยังไม่ได้คิดผลของครีมกันแดดหรือเสื้อผ้า
      </Text>

      {s.reapplyReminder ? (
        <View style={styles.block}>
          {reapplyDue ? (
            <Text style={styles.text} testID="reapply-at">
              จะเตือนทาครีมซ้ำราว {clockBkk(reapplyDue)}
            </Text>
          ) : null}
          {reapplyReason ? (
            <Text style={styles.hint} testID="reapply-reason">
              {reapplyReason}
            </Text>
          ) : null}
          {isDaylight ? (
            <Button
              label={reapplyDue ? 'ทาครีมอีกครั้งแล้ว' : 'ทาครีมแล้ว'}
              kind="outline"
              onPress={applied}
              testID="reapply-start"
            />
          ) : null}
        </View>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  block: { gap: 6 },
  value: { color: colors.text, fontSize: 15, fontWeight: '700' },
  text: { color: colors.text, fontSize: 14 },
  hint: { color: colors.muted, fontSize: 12 },
  primary: {
    alignSelf: 'flex-start',
    backgroundColor: colors.text,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  primaryText: { color: '#FFFFFF', fontWeight: '600' },
  outline: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: colors.text,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  outlineText: { color: colors.text, fontWeight: '600' },
});
