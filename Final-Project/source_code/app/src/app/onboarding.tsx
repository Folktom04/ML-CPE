import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';

import { Card, colors, Note } from '@/components/Card';
import { DISCLAIMER_TH } from '@/config';
import { requestLocationPermission } from '@/lib/location';
import {
  notificationPermission,
  notificationsAvailable,
  notifyUnavailableText,
} from '@/lib/notifications';
import { CONSENT_HINT_TH, CONSENT_LABEL_TH } from '@/lib/settings';
import { useSettings } from '@/lib/SettingsContext';
import { SKIN_DESCRIPTION_TH } from '@/lib/skinQuiz';

const STEPS = ['ยินดีต้อนรับ', 'ตำแหน่ง', 'ประเภทผิว', 'ความยินยอม'] as const;

function Button({
  label,
  onPress,
  kind = 'primary',
  disabled = false,
  testID,
}: {
  label: string;
  onPress: () => void;
  kind?: 'primary' | 'outline';
  disabled?: boolean;
  testID?: string;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[kind === 'primary' ? styles.primary : styles.outline, disabled && styles.disabled]}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      testID={testID}>
      <Text style={kind === 'primary' ? styles.primaryText : styles.outlineText}>{label}</Text>
    </Pressable>
  );
}

/**
 * First run (day 21): welcome -> location (GPS or a province) -> skin-type quiz -> consent ->
 * home. Every step can be done later in Settings; nothing is sent to the server without consent.
 */
export default function OnboardingScreen() {
  const router = useRouter();
  const { settings: s, update } = useSettings();
  const [step, setStep] = useState(0);
  const [denied, setDenied] = useState(false);
  const [notify, setNotify] = useState<boolean | null>(null);

  const useGps = async () => {
    setDenied(false);
    if (await requestLocationPermission()) {
      await update({ locationMode: 'gps' });
      setStep(2);
    } else {
      setDenied(true);
      router.push('/province');
    }
  };

  const finish = async () => {
    await update({ onboarded: true });
    router.replace('/');
  };

  const locationChosen =
    s.locationMode === 'gps' || (s.locationMode === 'province' && s.province !== null);

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.progress} testID="onboarding-step">
        ขั้นที่ {step + 1} จาก {STEPS.length} · {STEPS[step]}
      </Text>

      {step === 0 ? (
        <Card title="UV Guard">
          <Text style={styles.text}>
            ประเมินดัชนี UV, UVA และ UVB ณ ตำแหน่งของคุณ บอกระดับความเสี่ยงตามประเภทผิว
            และเวลาโดยประมาณก่อนผิวไหม้
          </Text>
          <Note>{DISCLAIMER_TH}</Note>
          <Button label="เริ่ม" onPress={() => setStep(1)} testID="onboarding-start" />
        </Card>
      ) : null}

      {step === 1 ? (
        <Card title="ตำแหน่งที่ใช้คำนวณ">
          <Text style={styles.text}>
            แอปใช้ตำแหน่งเพื่อดึงสภาพอากาศและคำนวณค่า UV ของพื้นที่นั้น ขอสิทธิ์เฉพาะตอนเปิดแอป
            ปัดพิกัดเหลือประมาณ 1 กม. ก่อนส่งไปคำนวณ และไม่เก็บพิกัด GPS ไว้ในเครื่อง
            ถ้าไม่อยากใช้ GPS เลือกจังหวัดเองได้
          </Text>
          {denied ? (
            <Note testID="location-denied">ไม่ได้รับสิทธิ์ตำแหน่ง เลือกจังหวัดแทนได้</Note>
          ) : null}
          {s.locationMode === 'province' && s.province ? (
            <Text style={styles.value} testID="chosen-province">
              จ.{s.province} (เลือกเอง)
            </Text>
          ) : null}
          {s.locationMode === 'gps' ? (
            <Text style={styles.value} testID="chosen-gps">
              ใช้ตำแหน่งปัจจุบัน (GPS)
            </Text>
          ) : null}
          <View style={styles.buttons}>
            <Button label="ใช้ตำแหน่งปัจจุบัน (GPS)" onPress={useGps} testID="use-gps" />
            <Button
              label="เลือกจังหวัดเอง"
              kind="outline"
              onPress={() => router.push('/province')}
              testID="pick-province"
            />
          </View>
          {notificationsAvailable() ? (
            <View style={styles.notify}>
              <Text style={styles.label}>การแจ้งเตือน (ไม่บังคับ)</Text>
              <Text style={styles.hint}>
                เตือนเมื่อ UV สูง สรุปทุกเช้า 07:00 และเตือนทาครีมซ้ำ ตั้งเวลาจากในเครื่อง
                ไม่ส่งข้อมูลออกจากมือถือ
              </Text>
              {notify === null ? (
                <Button
                  label="อนุญาตการแจ้งเตือน"
                  kind="outline"
                  onPress={async () => setNotify(await notificationPermission(true))}
                  testID="allow-notify"
                />
              ) : (
                <Text style={styles.value} testID="notify-result">
                  {notify ? 'อนุญาตการแจ้งเตือนแล้ว' : 'ไม่ได้อนุญาต แอปยังดูค่า UV ได้ตามปกติ'}
                </Text>
              )}
            </View>
          ) : notifyUnavailableText() ? (
            <Note testID="onboarding-notify-unavailable">
              {notifyUnavailableText()} · แอปยังดูค่า UV ได้ตามปกติ
            </Note>
          ) : null}
          <Button
            label="ถัดไป"
            onPress={() => setStep(2)}
            disabled={!locationChosen}
            testID="location-next"
          />
        </Card>
      ) : null}

      {step === 2 ? (
        <Card title="ประเภทผิว">
          <Text style={styles.text}>
            ประเภทผิวใช้คำนวณเวลาก่อนผิวไหม้ ตอบ 5 ข้อ หรือเลือกประเภทเองก็ได้
          </Text>
          {s.skinType ? (
            <Text style={styles.value} testID="chosen-skin">
              ผิวประเภท {s.skinType} · {SKIN_DESCRIPTION_TH[s.skinType]}
            </Text>
          ) : null}
          <Button
            label={s.skinType ? 'ทำแบบสอบถามใหม่' : 'ทำแบบสอบถาม 5 ข้อ'}
            kind={s.skinType ? 'outline' : 'primary'}
            onPress={() => router.push('/quiz')}
            testID="open-quiz"
          />
          <View style={styles.buttons}>
            {s.skinType ? (
              <Button label="ถัดไป" onPress={() => setStep(3)} testID="skin-next" />
            ) : (
              <Button
                label="ข้ามไปก่อน (ใช้ประเภท III ชั่วคราว)"
                kind="outline"
                onPress={() => setStep(3)}
                testID="skin-skip"
              />
            )}
          </View>
        </Card>
      ) : null}

      {step === 3 ? (
        <Card title="ส่งข้อมูลไปเซิร์ฟเวอร์ (ไม่บังคับ)">
          <View style={styles.row}>
            <View style={styles.rowText}>
              <Text style={styles.label}>{CONSENT_LABEL_TH}</Text>
              <Text style={styles.hint}>{CONSENT_HINT_TH}</Text>
            </View>
            <Switch
              value={s.serverConsent}
              onValueChange={(v) => update({ serverConsent: v })}
              accessibilityLabel="ยินยอมให้ส่งข้อมูลไปเซิร์ฟเวอร์"
              testID="consent-switch"
            />
          </View>
          <Text style={styles.hint}>
            ถ้าไม่ยินยอม แอปยังดูค่า UV ได้ตามปกติ การตั้งค่าทั้งหมดเก็บในเครื่อง
          </Text>
          <Button label="เริ่มใช้งาน" onPress={finish} testID="onboarding-finish" />
        </Card>
      ) : null}

      {step > 0 ? (
        <Pressable onPress={() => setStep(step - 1)} accessibilityRole="button" testID="back">
          <Text style={styles.back}>ย้อนกลับ</Text>
        </Pressable>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 16, gap: 12, maxWidth: 640, width: '100%', alignSelf: 'center' },
  progress: { color: colors.muted, fontSize: 13 },
  text: { color: colors.text, fontSize: 15, lineHeight: 22 },
  value: { color: colors.text, fontSize: 15, fontWeight: '700' },
  label: { color: colors.text, fontSize: 15, fontWeight: '600' },
  hint: { color: colors.muted, fontSize: 13 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  rowText: { flex: 1, gap: 2 },
  buttons: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
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
    paddingVertical: 10,
  },
  outlineText: { color: colors.text, fontWeight: '600' },
  disabled: { opacity: 0.4 },
  notify: { gap: 4, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 8 },
  back: { color: colors.muted, textAlign: 'center', paddingVertical: 8 },
});
