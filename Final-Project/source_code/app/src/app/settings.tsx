import { useRouter } from 'expo-router';
import { useEffect, useState, type ReactNode } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';

import { describeError } from '@/api/client';
import { Card, colors, Note } from '@/components/Card';
import { requestLocationPermission } from '@/lib/location';
import {
  notificationPermission,
  notificationsAvailable,
  notifyUnavailableText,
  WITHOUT_NOTIFY_TH,
} from '@/lib/notifications';
import { useSettings } from '@/lib/SettingsContext';
import {
  ALERT_THRESHOLDS,
  CONSENT_HINT_TH,
  CONSENT_LABEL_TH,
  safeThresholdFor,
  type AlertThreshold,
} from '@/lib/settings';
import { SKIN_DESCRIPTION_TH } from '@/lib/skinQuiz';
import { WHO_LEVELS, levelIndex } from '@/lib/uv';

function Row({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <View style={styles.row}>
      <View style={styles.rowText}>
        <Text style={styles.label}>{label}</Text>
        {hint ? <Text style={styles.hint}>{hint}</Text> : null}
      </View>
      {children}
    </View>
  );
}

function Segments<T extends number>({
  values,
  value,
  onChange,
  format,
  testID,
}: {
  values: readonly T[];
  value: T;
  onChange: (v: T) => void;
  format: (v: T) => string;
  testID: string;
}) {
  return (
    <View style={styles.segments}>
      {values.map((v) => {
        const on = v === value;
        return (
          <Pressable
            key={v}
            onPress={() => onChange(v)}
            style={[styles.segment, on && styles.segmentOn]}
            accessibilityRole="radio"
            accessibilityState={{ checked: on }}
            testID={`${testID}-${v}`}>
            <Text style={[styles.segmentText, on && styles.segmentTextOn]}>{format(v)}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

/** Settings: skin type, alert toggles and thresholds, and deleting my data. */
export default function SettingsScreen() {
  const router = useRouter();
  const { settings: s, ready, sync, update, deleteMyData, pushActive } = useSettings();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleted, setDeleted] = useState(false);
  const [gpsDenied, setGpsDenied] = useState(false);
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    notificationPermission(false).then((ok) => {
      if (active) setAllowed(ok);
    });
    return () => {
      active = false;
    };
  }, []);

  if (!ready) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
      </View>
    );
  }

  const onDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteMyData();
      setConfirming(false);
      setDeleted(true);
    } catch (err) {
      setDeleteError(
        `ลบข้อมูลบนเซิร์ฟเวอร์ไม่สำเร็จ ข้อมูลในเครื่องยังอยู่ ลองใหม่อีกครั้ง (${describeError(err)})`,
      );
    } finally {
      setDeleting(false);
    }
  };

  const safe = safeThresholdFor(s.alertThreshold);
  // Without the notifications module (Expo Go on Android) the switches are shown off and
  // disabled ON SCREEN ONLY: the stored values (and notify_enabled on the server) stay as they
  // are, so a development build later works with the user's own choices.
  const available = notificationsAvailable();
  const unavailable = notifyUnavailableText();

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Card title="ประเภทผิว">
        <Text style={styles.value} testID="settings-skin">
          {s.skinType ? `ประเภท ${s.skinType}` : 'ยังไม่ได้ระบุ (ใช้ประเภท III ชั่วคราว)'}
        </Text>
        {s.skinType ? <Text style={styles.hint}>{SKIN_DESCRIPTION_TH[s.skinType]}</Text> : null}
        <Pressable
          style={styles.buttonOutline}
          onPress={() => router.push('/quiz')}
          accessibilityRole="button"
          testID="open-quiz">
          <Text style={styles.buttonOutlineText}>
            {s.skinType ? 'ทำแบบสอบถามใหม่' : 'ทำแบบสอบถามประเภทผิว'}
          </Text>
        </Pressable>
      </Card>

      <Card title="ส่งข้อมูลไปเซิร์ฟเวอร์">
        <Row
          label={CONSENT_LABEL_TH}
          hint={CONSENT_HINT_TH}>
          <Switch
            value={s.serverConsent}
            onValueChange={(v) => update({ serverConsent: v })}
            accessibilityLabel="ยินยอมให้ส่งข้อมูลไปเซิร์ฟเวอร์"
            testID="consent-switch"
          />
        </Row>
        {!s.skinType && s.serverConsent ? (
          <Text style={styles.hint}>จะส่งเมื่อระบุประเภทผิวแล้ว</Text>
        ) : null}
      </Card>

      <Card title="แจ้งเตือนเมื่อ UV สูง">
        {unavailable ? (
          <Note testID="notify-unavailable">
            {unavailable} · {WITHOUT_NOTIFY_TH}
          </Note>
        ) : null}
        <Row
          label="เปิดการแจ้งเตือน"
          hint="แจ้งเตือนจากในเครื่อง ตั้งเวลาล่วงหน้าจากพยากรณ์ ไม่ส่งข้อมูลออกจากมือถือ ใช้ได้โดยไม่ต้องยินยอม">
          <Switch
            value={available ? s.notifyEnabled : false}
            disabled={!available}
            onValueChange={async (v) => {
              if (!available) return;
              if (v) setAllowed(await notificationPermission(true));
              await update({ notifyEnabled: v });
            }}
            accessibilityLabel="เปิดการแจ้งเตือนเมื่อ UV สูง"
            testID="notify-switch"
          />
        </Row>
        {available && allowed === false ? (
          <Note testID="notify-not-allowed">
            ยังไม่ได้อนุญาตการแจ้งเตือนของเครื่อง จึงไม่มีการแจ้งเตือนเด้งขึ้นมา เปิดสิทธิ์ได้ในการตั้งค่าของเครื่อง
          </Note>
        ) : null}
        <Text style={styles.hint} testID="notify-limits">
          ต้องเปิดแอปอย่างน้อยวันละครั้ง (พยากรณ์ในเครื่องมีประมาณ 36 ชม.) ถ้าไม่ได้เปิด จะมีแจ้งเตือน
          &quot;เปิดแอปเพื่อดู UV วันนี้&quot; ตอน 07:00 แทน · Android อาจส่งแจ้งเตือนช้ากว่าเวลาที่ตั้ง
          (โหมดประหยัดแบตเตอรี่) · การแจ้งเตือน &quot;UV สูง&quot; / &quot;ปลอดภัยแล้ว&quot; จากเซิร์ฟเวอร์
          (ขณะไม่ได้เปิดแอป) ต้องยินยอมให้ส่งข้อมูลและใช้ development build (Expo Go บน Android
          รับไม่ได้) และถ้าเซิร์ฟเวอร์ปิด push จะไม่มา
        </Text>
        {pushActive ? (
          <Note testID="push-status">
            การแจ้งเตือน &quot;UV สูง&quot; และ &quot;ปลอดภัยแล้ว&quot; ส่งจากเซิร์ฟเวอร์ทุก 30 นาที ตามจังหวัด
            จ.{s.province} แทนการตั้งเวลาในเครื่อง · ตรวจทุกครั้งที่เปิดแอป ถ้าเซิร์ฟเวอร์ปิดหลังจากนั้น
            push จะไม่มาจนกว่าจะเปิดแอปครั้งถัดไป
          </Note>
        ) : s.serverConsent && s.province === null ? (
          <Note testID="push-no-province">
            ยังไม่รู้จังหวัด การแจ้งเตือนจากเซิร์ฟเวอร์จึงยังไม่ทำงาน (ใช้การแจ้งเตือนในเครื่องแทน)
            เปิด GPS หรือเลือกจังหวัด
          </Note>
        ) : null}
        <Text style={styles.label}>เตือนเมื่อ UV ถึงระดับ</Text>
        <Segments
          values={ALERT_THRESHOLDS}
          value={s.alertThreshold}
          onChange={(v: AlertThreshold) => update({ alertThreshold: v })}
          format={(v) => `${WHO_LEVELS[levelIndex(v)]} (${v}+)`}
          testID="threshold"
        />
        <Text style={styles.hint} testID="threshold-hint">
          เตือนเมื่อ UVI ตั้งแต่ {s.alertThreshold} ขึ้นไป และแจ้งว่า &quot;ปลอดภัยแล้ว&quot; เมื่อต่ำกว่า{' '}
          {safe} (ปัดเศษแบบเดียวกับระดับ WHO เช่น 7.8 นับเป็น 8) · เตือนประเภทเดียวกันไม่เกิน 1 ครั้งใน 3
          ชม. และไม่เตือนหลังพระอาทิตย์ตก
        </Text>
      </Card>

      <Card title="แจ้งเตือนในเครื่อง">
        <Row label="สรุป UV ทุกเช้า 07:00">
          <Switch
            value={available ? s.dailySummary : false}
            disabled={!available}
            onValueChange={(v) => (available ? update({ dailySummary: v }) : undefined)}
            accessibilityLabel="สรุป UV ทุกเช้า"
            testID="daily-switch"
          />
        </Row>
        <Row label="เตือนทาครีมกันแดดซ้ำทุก 2 ชม.">
          <Switch
            value={available ? s.reapplyReminder : false}
            disabled={!available}
            onValueChange={(v) => (available ? update({ reapplyReminder: v }) : undefined)}
            accessibilityLabel="เตือนทาครีมกันแดดซ้ำ"
            testID="reapply-switch"
          />
        </Row>
        <Text style={styles.hint}>
          เตือนทาครีมซ้ำเริ่มนับเมื่อกด &quot;ทาครีมแล้ว&quot; ในหน้าหลัก ส่วนเตือนก่อนผิวไหม้เริ่มเมื่อกด
          &quot;ออกแดด&quot; (เตือนที่ประมาณ 80 % ของปริมาณ UV ที่ทำให้ผิวแดง)
        </Text>
      </Card>

      <Card title="ตำแหน่ง">
        <Text style={styles.value} testID="settings-location">
          {s.locationMode === 'gps'
            ? 'ตำแหน่งปัจจุบัน (GPS) · จังหวัดดูได้ที่หน้าหลัก'
            : s.locationMode === 'province' && s.province
              ? `จ.${s.province} (เลือกเอง)`
              : 'ปทุมธานี (ตำแหน่งเริ่มต้น)'}
        </Text>
        {gpsDenied ? (
          <Note testID="settings-gps-denied">
            ไม่ได้รับสิทธิ์ตำแหน่ง เปิดสิทธิ์ได้ในการตั้งค่าของเครื่อง หรือเลือกจังหวัดแทน
          </Note>
        ) : null}
        <View style={styles.segments}>
          {s.locationMode !== 'gps' ? (
            <Pressable
              style={styles.buttonOutline}
              onPress={async () => {
                const ok = await requestLocationPermission();
                setGpsDenied(!ok);
                if (ok) await update({ locationMode: 'gps' });
              }}
              accessibilityRole="button"
              testID="settings-use-gps">
              <Text style={styles.buttonOutlineText}>ใช้ GPS</Text>
            </Pressable>
          ) : null}
          <Pressable
            style={styles.buttonOutline}
            onPress={() => router.push('/province')}
            accessibilityRole="button"
            testID="settings-pick-province">
            <Text style={styles.buttonOutlineText}>เลือกจังหวัด</Text>
          </Pressable>
        </View>
        <Text style={styles.hint}>
          โมเดลฝึกและทดสอบด้วยข้อมูลของปทุมธานีเท่านั้น ถ้าอยู่ห่างเกิน 50 กม.
          ความแม่นยำยังไม่ได้ประเมิน · รองรับเฉพาะพื้นที่ประเทศไทย
        </Text>
      </Card>

      <Text style={styles.sync} testID="sync-state">
        {sync.kind === 'syncing' && 'กำลังบันทึกไปยังเซิร์ฟเวอร์…'}
        {sync.kind === 'ok' && 'บันทึกในเครื่องและบนเซิร์ฟเวอร์แล้ว'}
        {sync.kind === 'error' && `บันทึกในเครื่องแล้ว แต่ยังไม่ได้ซิงก์กับเซิร์ฟเวอร์: ${sync.message}`}
        {sync.kind === 'idle' &&
          (s.serverConsent
            ? 'การตั้งค่าบันทึกในเครื่องทันทีที่เปลี่ยน'
            : 'การตั้งค่าเก็บในเครื่องเท่านั้น (ยังไม่ได้ยินยอมให้ส่งไปเซิร์ฟเวอร์)')}
      </Text>

      <Card title="ข้อมูลของฉัน">
        <Text style={styles.hint} testID="my-data-text">
          ถ้ายินยอม เซิร์ฟเวอร์จะเก็บเฉพาะรหัสอุปกรณ์แบบสุ่ม ประเภทผิว จังหวัด (ไม่เก็บพิกัด GPS)
          การตั้งค่าการแจ้งเตือน และรหัสรับการแจ้งเตือนของเครื่อง (push token) ไม่มีชื่อ อีเมล หรือรูปภาพ
        </Text>
        {deleted ? (
          <Note testID="deleted-note">ลบข้อมูลทั้งหมดแล้ว ทั้งบนเซิร์ฟเวอร์และในเครื่อง</Note>
        ) : null}
        {!confirming ? (
          <Pressable
            style={styles.danger}
            onPress={() => {
              setDeleted(false);
              setConfirming(true);
            }}
            accessibilityRole="button"
            testID="delete-start">
            <Text style={styles.dangerText}>ลบข้อมูลของฉัน</Text>
          </Pressable>
        ) : (
          <View style={styles.confirm} testID="delete-confirm">
            <Text style={styles.label}>ยืนยันการลบข้อมูล?</Text>
            <Text style={styles.hint}>
              จะลบบัญชีผู้ใช้และข้อมูลที่ผูกไว้ทั้งหมดบนเซิร์ฟเวอร์ (การตั้งค่า ประวัติค่า UV
              ประวัติการแจ้งเตือน) และล้างการตั้งค่าในเครื่อง ย้อนกลับไม่ได้
            </Text>
            {deleteError ? (
              <Text style={styles.error} testID="delete-error">
                {deleteError}
              </Text>
            ) : null}
            <View style={styles.confirmButtons}>
              <Pressable
                style={styles.danger}
                onPress={onDelete}
                disabled={deleting}
                accessibilityRole="button"
                testID="delete-confirm-yes">
                <Text style={styles.dangerText}>{deleting ? 'กำลังลบ…' : 'ยืนยันลบ'}</Text>
              </Pressable>
              <Pressable
                style={styles.buttonOutline}
                onPress={() => {
                  setConfirming(false);
                  setDeleteError(null);
                }}
                disabled={deleting}
                accessibilityRole="button"
                testID="delete-cancel">
                <Text style={styles.buttonOutlineText}>ยกเลิก</Text>
              </Pressable>
            </View>
          </View>
        )}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 16, gap: 12, maxWidth: 640, width: '100%', alignSelf: 'center' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  rowText: { flex: 1, gap: 2 },
  label: { color: colors.text, fontSize: 15, fontWeight: '600' },
  value: { color: colors.text, fontSize: 18, fontWeight: '700' },
  hint: { color: colors.muted, fontSize: 13 },
  segments: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  segment: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  segmentOn: { backgroundColor: colors.text, borderColor: colors.text },
  segmentText: { color: colors.text, fontWeight: '600' },
  segmentTextOn: { color: '#FFFFFF' },
  sync: { color: colors.muted, fontSize: 12, textAlign: 'center' },
  buttonOutline: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: colors.text,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  buttonOutlineText: { color: colors.text, fontWeight: '600' },
  danger: {
    alignSelf: 'flex-start',
    backgroundColor: '#B42318',
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  dangerText: { color: '#FFFFFF', fontWeight: '600' },
  confirm: { gap: 8 },
  confirmButtons: { flexDirection: 'row', gap: 8 },
  error: { color: '#B42318', fontSize: 13 },
});
