import { LightSensor } from 'expo-sensors';
import { useEffect, useRef, useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text } from 'react-native';

import { Card, colors, Note } from '@/components/Card';
import { DISCLAIMER_TH } from '@/config';
import { formatLux, LUX_WINDOW_S, medianLux, pushLux, type LuxSample } from '@/lib/lux';
import { faceUpMessage, faceUpStatus, screenTiltDeg } from '@/lib/orientation';
import { useGravity } from '@/lib/useGravity';

const LIGHT_INTERVAL_MS = 250;

type Availability = 'checking' | 'yes' | 'no';

/** Ambient light (Android only) + "is the screen facing the sky?" check. Uncalibrated. */
export default function LightScreen() {
  const android = Platform.OS === 'android';
  const [available, setAvailable] = useState<Availability>(android ? 'checking' : 'no');
  const [lux, setLux] = useState<number | null>(null);
  const samples = useRef<LuxSample[]>([]);
  const gravity = useGravity();

  useEffect(() => {
    if (!android) return;
    let sub: { remove: () => void } | null = null;
    let active = true;
    LightSensor.isAvailableAsync()
      .then((ok) => {
        if (!active) return;
        setAvailable(ok ? 'yes' : 'no');
        if (!ok) return;
        LightSensor.setUpdateInterval(LIGHT_INTERVAL_MS);
        sub = LightSensor.addListener(({ illuminance }) => {
          samples.current = pushLux(samples.current, { lux: illuminance, t: Date.now() / 1000 });
          setLux(medianLux(samples.current));
        });
      })
      .catch(() => active && setAvailable('no'));
    return () => {
      active = false;
      sub?.remove();
    };
  }, [android]);

  const tilt = gravity ? screenTiltDeg(gravity, Platform.OS) : null;
  const status = faceUpStatus(tilt);

  let body;
  if (!android) {
    body = (
      <Card title="วัดแสง">
        <Text style={styles.text} testID="light-android-only">
          ใช้ได้เฉพาะ Android (iOS ไม่เปิดให้แอปอ่านเซนเซอร์แสง)
        </Text>
      </Card>
    );
  } else if (available === 'no') {
    body = (
      <Card title="วัดแสง">
        <Text style={styles.text} testID="light-unavailable">
          มือถือเครื่องนี้ไม่มีเซนเซอร์แสงที่แอปอ่านได้
        </Text>
      </Card>
    );
  } else {
    body = (
      <>
        <Card title={`ความสว่าง (ค่ากลางของ ${LUX_WINDOW_S} วินาทีล่าสุด)`}>
          <Text style={styles.big} testID="lux-value">
            {lux === null ? '—' : formatLux(lux)}
          </Text>
          <Text
            style={[styles.text, { color: status === 'face_up' ? '#2E7D3E' : '#B3261E' }]}
            testID="orientation-status">
            {faceUpMessage(status, tilt)}
          </Text>
          {status === 'face_up' ? null : (
            <Text style={styles.small} testID="lux-not-usable">
              ค่าที่อ่านได้ตอนนี้ยังไม่ควรใช้ จนกว่าจะวางหน้าจอหงายขึ้นฟ้า
            </Text>
          )}
        </Card>
        <Note testID="lux-uncalibrated">
          ค่า lux ยังไม่ได้ปรับเทียบ (วัน 25) · ใช้ดูเท่านั้น ไม่เปลี่ยนค่า UVI
        </Note>
        <Text style={styles.small}>
          เซนเซอร์แสงอยู่ด้านหน้าจอ ใกล้กล้องหน้า อย่าให้นิ้วหรือเคสบัง
          มือถือหลายรุ่นอ่านค่าได้ไม่เกินระดับหนึ่ง ค่าจึงอาจตันเมื่อแดดจัด
        </Text>
      </>
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      {body}
      <Text style={styles.disclaimer}>{DISCLAIMER_TH}</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 16, gap: 12, maxWidth: 640, width: '100%', alignSelf: 'center' },
  big: { color: colors.text, fontSize: 36, fontWeight: '700' },
  text: { color: colors.text, fontSize: 15 },
  small: { color: colors.muted, fontSize: 13 },
  disclaimer: { color: colors.muted, fontSize: 12, textAlign: 'center', paddingVertical: 8 },
});
