import { CameraView, useCameraPermissions } from 'expo-camera';
import { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { ApiError, describeError } from '@/api/client';
import type { SkyImageResponse } from '@/api/types';
import { Card, colors, Note } from '@/components/Card';
import { DISCLAIMER_TH } from '@/config';
import { cameraAimHint, cameraElevationDeg } from '@/lib/orientation';
import { useSettings } from '@/lib/SettingsContext';
import { pct, SKY_DOMAIN_GAP_TH, SKY_NOTICE_TH, SKY_SUPPORTING_TH, skyView } from '@/lib/sky';
import { analyzeSkyPhoto } from '@/lib/skyPhoto';
import { useGravity } from '@/lib/useGravity';

type Shot =
  | { kind: 'idle' }
  | { kind: 'busy' }
  | { kind: 'ok'; data: SkyImageResponse }
  | { kind: 'error'; message: string; detail: string };

function SkyResult({ data }: { data: SkyImageResponse }) {
  const v = skyView(data);
  return (
    <Card title="ผลวิเคราะห์ท้องฟ้า">
      {v.kind === 'sure' ? (
        <Text style={styles.big} testID="sky-class">
          {v.nameTh}
        </Text>
      ) : (
        <View testID="sky-unsure" style={styles.gap4}>
          <Text style={styles.big}>ไม่แน่ใจ</Text>
          <Text style={styles.text}>ที่เป็นไปได้มากที่สุด 2 อันดับ:</Text>
          {v.top.map((c, i) => (
            <Text key={c.name} style={styles.text} testID={`sky-top-${i + 1}`}>
              {i + 1}. {c.nameTh} ({pct(c.prob)})
            </Text>
          ))}
        </View>
      )}
      <Text style={styles.text} testID="sky-confidence">
        ความมั่นใจของโมเดล: {pct(v.confidence)}
      </Text>
      <Text style={styles.text} testID="sky-cloud">
        สัดส่วนเมฆ (ประมาณจากสีแดง/น้ำเงิน): {pct(v.cloudFraction)}
      </Text>
      <Note testID="sky-supporting">{SKY_SUPPORTING_TH} · ไม่บันทึกภาพ</Note>
      <Text style={styles.small} testID="sky-domain-gap">
        หมายเหตุ: {SKY_DOMAIN_GAP_TH}
      </Text>
      {Object.entries(data.reliability).map(([k, t]) => (
        <Text key={k} style={styles.small}>
          {k === 'sky_class' ? 'สภาพท้องฟ้า' : 'สัดส่วนเมฆ'}: {t}
        </Text>
      ))}
    </Card>
  );
}

/** Camera: sky photo → /sky-image (supporting information only, never changes the UVI). */
export default function CameraScreen() {
  const { settings, ready, update } = useSettings();
  const [permission, requestPermission] = useCameraPermissions();
  const camera = useRef<CameraView>(null);
  const [shot, setShot] = useState<Shot>({ kind: 'idle' });
  const gravity = useGravity();
  const hint = gravity ? cameraAimHint(cameraElevationDeg(gravity, Platform.OS)) : null;

  const takeAndAnalyze = useCallback(async () => {
    if (!camera.current) return;
    setShot({ kind: 'busy' });
    try {
      const photo = await camera.current.takePictureAsync({ quality: 0.8, exif: false });
      if (!photo) throw new Error('no photo');
      setShot({ kind: 'ok', data: await analyzeSkyPhoto(photo) });
    } catch (err) {
      setShot({
        kind: 'error',
        message: err instanceof ApiError ? err.message : 'ถ่ายหรือส่งภาพไม่สำเร็จ ลองใหม่อีกครั้ง',
        detail: err instanceof ApiError ? (err.detail ?? '') : describeError(err),
      });
    }
  }, []);

  let body;
  if (!ready || !permission) {
    body = <ActivityIndicator size="large" testID="camera-loading" />;
  } else if (!settings.skyNoticeAck) {
    body = (
      <Card title="ก่อนถ่ายภาพท้องฟ้า">
        <Text style={styles.text} testID="sky-notice">
          {SKY_NOTICE_TH}
        </Text>
        <Text style={styles.small}>
          ภาพใช้ดูสภาพท้องฟ้าประกอบเท่านั้น ไม่นำไปฝึกโมเดล และไม่เปลี่ยนค่า UVI
        </Text>
        <Pressable
          style={styles.button}
          accessibilityRole="button"
          testID="sky-notice-ack"
          onPress={() => update({ skyNoticeAck: true })}>
          <Text style={styles.buttonText}>รับทราบ</Text>
        </Pressable>
      </Card>
    );
  } else if (!permission.granted) {
    body = (
      <Card title="ต้องใช้สิทธิ์กล้อง">
        <Text style={styles.text} testID="camera-denied">
          แอปต้องใช้กล้องเพื่อถ่ายภาพท้องฟ้า ส่วนอื่นของแอปยังใช้ได้ตามปกติ
        </Text>
        {permission.canAskAgain ? (
          <Pressable
            style={styles.button}
            accessibilityRole="button"
            testID="camera-request"
            onPress={requestPermission}>
            <Text style={styles.buttonText}>อนุญาตให้ใช้กล้อง</Text>
          </Pressable>
        ) : (
          <Text style={styles.small}>เปิดสิทธิ์กล้องได้ที่ การตั้งค่าของเครื่อง → แอป</Text>
        )}
      </Card>
    );
  } else {
    body = (
      <>
        <View style={styles.cameraBox}>
          <CameraView ref={camera} style={styles.camera} facing="back" testID="camera-view" />
        </View>
        <Text style={styles.small}>
          หันกล้องขึ้นฟ้าให้เห็นแต่ท้องฟ้า และอย่าเล็งดวงอาทิตย์ตรง ๆ
        </Text>
        {hint ? <Note testID="camera-aim-hint">{hint}</Note> : null}
        <Pressable
          style={[styles.button, shot.kind === 'busy' && styles.disabled]}
          accessibilityRole="button"
          testID="camera-shoot"
          disabled={shot.kind === 'busy'}
          onPress={takeAndAnalyze}>
          <Text style={styles.buttonText}>
            {shot.kind === 'busy' ? 'กำลังวิเคราะห์…' : 'ถ่ายและวิเคราะห์'}
          </Text>
        </Pressable>
        {shot.kind === 'ok' ? <SkyResult data={shot.data} /> : null}
        {shot.kind === 'error' ? (
          <Card title="วิเคราะห์ไม่สำเร็จ">
            <Text style={styles.text} testID="camera-error">
              {shot.message}
            </Text>
            {shot.detail ? <Text style={styles.small}>รายละเอียด: {shot.detail}</Text> : null}
          </Card>
        ) : null}
      </>
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      {body}
      <Text style={styles.disclaimer}>
        {shot.kind === 'ok' ? shot.data.disclaimer : DISCLAIMER_TH}
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 16, gap: 12, maxWidth: 640, width: '100%', alignSelf: 'center' },
  cameraBox: { borderRadius: 16, overflow: 'hidden', aspectRatio: 3 / 4, width: '100%' },
  camera: { flex: 1 },
  big: { color: colors.text, fontSize: 24, fontWeight: '700' },
  text: { color: colors.text, fontSize: 15 },
  small: { color: colors.muted, fontSize: 13 },
  gap4: { gap: 4 },
  button: {
    alignSelf: 'flex-start',
    backgroundColor: colors.text,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  disabled: { opacity: 0.5 },
  buttonText: { color: '#FFFFFF', fontWeight: '600' },
  disclaimer: { color: colors.muted, fontSize: 12, textAlign: 'center', paddingVertical: 8 },
});
