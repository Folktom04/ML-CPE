import { CameraView, useCameraPermissions } from 'expo-camera';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { ApiError, describeError, fetchForecast } from '@/api/client';
import type { SkyImageResponse } from '@/api/types';
import { Card, colors, Note, ui } from '@/components/Card';
import { DISCLAIMER_TH } from '@/config';
import { resolvePlace } from '@/lib/location';
import { cameraAimHint, cameraElevationDeg, lowAngleWarning } from '@/lib/orientation';
import { useSettings } from '@/lib/SettingsContext';
import {
  CLOUD_CLEAR_NOTE_TH,
  CLOUD_IN_IMAGE_TH,
  cloudLevelTh,
  compareCloud,
  pct,
  rankedClasses,
  RELIABILITY_LABEL_TH,
  SKY_DOMAIN_GAP_TH,
  SKY_NOTICE_TH,
  SKY_SUPPORTING_TH,
  SKY_UV_MEANING_TH,
  SKY_UV_SOURCE_TH,
  skyView,
  type CloudCheck,
  type SkyView,
} from '@/lib/sky';
import { analyzeSkyPhoto } from '@/lib/skyPhoto';
import { useGravity } from '@/lib/useGravity';

type Shot =
  | { kind: 'idle' }
  | { kind: 'busy' }
  | { kind: 'ok'; data: SkyImageResponse; elevationDeg: number | null }
  | { kind: 'error'; message: string; detail: string };

type Forecast = { kind: 'loading' } | { kind: 'ok'; cloudPct: number | null } | { kind: 'error' };

const VERDICT: Record<CloudCheck['verdict'], { label: string; color: string }> = {
  match: { label: 'ตรงกัน', color: '#248A3D' },
  close: { label: 'ใกล้เคียง', color: '#C93400' },
  differ: { label: 'ต่างกัน', color: '#D70015' },
};

/** Six sky classes as bars, the most likely first. */
function ProbBars({ probs }: { probs: Record<string, number> }) {
  return (
    <View style={styles.gap8}>
      {rankedClasses(probs).map((c, i) => (
        <View key={c.name} testID={`sky-prob-${c.name}`} style={styles.gap4}>
          <View style={styles.row}>
            <Text style={[styles.text, i === 0 && styles.bold]}>{c.nameTh}</Text>
            <Text style={[styles.text, i === 0 && styles.bold]}>{pct(c.prob)}</Text>
          </View>
          <View style={styles.track}>
            <View
              style={[
                styles.fill,
                { width: `${Math.max(2, c.prob * 100)}%` },
                i === 0 ? styles.fillTop : null,
              ]}
            />
          </View>
        </View>
      ))}
    </View>
  );
}

/** Photo cloud level next to the forecast cloud cover the UV model used for this hour. */
function CompareCard({ view, forecast }: { view: SkyView; forecast: Forecast }) {
  let body;
  if (forecast.kind === 'loading') {
    body = (
      <Text style={styles.small} testID="sky-compare-loading">
        กำลังดึงพยากรณ์เมฆของชั่วโมงนี้…
      </Text>
    );
  } else if (forecast.kind === 'error') {
    body = (
      <Text style={styles.small} testID="sky-compare-error">
        ดึงพยากรณ์ไม่สำเร็จ ผลวิเคราะห์ภาพยังใช้ได้ตามปกติ
      </Text>
    );
  } else {
    const check = compareCloud(view, forecast.cloudPct);
    body = check ? (
      <View style={styles.gap8} testID="sky-compare">
        <View style={styles.compareRow}>
          <View style={styles.cell}>
            <Text style={ui.eyebrow}>ในภาพของคุณ</Text>
            <Text style={styles.cellValue}>เมฆ{check.photoLevel}</Text>
          </View>
          <View style={styles.cell}>
            <Text style={ui.eyebrow}>พยากรณ์ที่โมเดล UV ใช้</Text>
            <Text style={styles.cellValue}>
              เมฆ{check.forecastLevel} ({Math.round(check.forecastPct)}%)
            </Text>
          </View>
        </View>
        <Text
          style={[styles.verdict, { color: VERDICT[check.verdict].color }]}
          testID="sky-compare-verdict">
          {VERDICT[check.verdict].label}
        </Text>
        <Text style={styles.text}>{check.message}</Text>
      </View>
    ) : (
      <Text style={styles.small} testID="sky-compare-none">
        พยากรณ์ชั่วโมงนี้ไม่มีข้อมูลเมฆ
      </Text>
    );
  }
  return (
    <Card title="เทียบกับพยากรณ์">
      {body}
      <Text style={styles.small}>
        เทียบเพื่อดูว่าพยากรณ์ตอนนี้เชื่อได้แค่ไหน ภาพเห็นท้องฟ้าแค่บางส่วน และไม่เปลี่ยนค่า UVI
      </Text>
    </Card>
  );
}

function SkyResult({
  data,
  elevationDeg,
  forecast,
}: {
  data: SkyImageResponse;
  elevationDeg: number | null;
  forecast: Forecast;
}) {
  const [details, setDetails] = useState(false);
  const v = skyView(data);
  const lowAngle = lowAngleWarning(elevationDeg);
  const top = rankedClasses(data.sky_class_probs)[0];
  const meaning = top ? SKY_UV_MEANING_TH[top.name] : undefined;
  return (
    <>
      <Card title="ผลวิเคราะห์ท้องฟ้า">
        {lowAngle ? <Note testID="sky-low-angle">{lowAngle}</Note> : null}
        {data.cloud_overlay ? (
          <View style={styles.gap8}>
            <Image
              source={{ uri: data.cloud_overlay }}
              style={styles.overlay}
              accessibilityLabel="ภาพที่ AI วิเคราะห์ ส่วนสีส้มคือเมฆ"
              testID="sky-overlay"
            />
            <View style={styles.legend}>
              <View style={styles.swatch} />
              <Text style={styles.small} testID="sky-overlay-legend">
                สีส้ม = ส่วนที่นับเป็นเมฆ (ประมาณจากสีแดง/น้ำเงิน) · ภาพไม่ถูกบันทึก
              </Text>
            </View>
          </View>
        ) : null}
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
        {v.cloudFractionCnn !== null ? (
          <View style={styles.gap4}>
            <Text style={styles.text} testID="sky-cloud-cnn">
              เมฆในภาพ (โมเดล): {cloudLevelTh(v.cloudFractionCnn)}
            </Text>
            <Text style={styles.small} testID="sky-cloud-cnn-note">
              {CLOUD_IN_IMAGE_TH}
            </Text>
          </View>
        ) : null}
        <Note testID="sky-supporting">{SKY_SUPPORTING_TH} · ไม่บันทึกภาพ</Note>
      </Card>

      <Card title="AI มั่นใจแค่ไหน">
        <ProbBars probs={data.sky_class_probs} />
        <Text style={styles.small}>
          โมเดล CNN แยกท้องฟ้า 6 แบบ ฝึกจากชุดภาพสาธารณะ SWIMCAT-ext ไม่ใช้ภาพจากแอป
        </Text>
      </Card>

      {meaning ? (
        <Card title="แปลว่าอะไรกับ UV">
          <Text style={styles.body} testID="sky-uv-meaning">
            {v.kind === 'unsure' ? `ถ้าเป็น${top.nameTh}: ` : ''}
            {meaning}
          </Text>
          <Text style={styles.small}>ใช้ค่า UV ในหน้าหลักเป็นหลักเสมอ ภาพนี้ไม่เปลี่ยนค่า UVI</Text>
          <Text style={styles.small} testID="sky-uv-source">
            {SKY_UV_SOURCE_TH}
          </Text>
        </Card>
      ) : null}

      <CompareCard view={v} forecast={forecast} />

      <Pressable
        onPress={() => setDetails((d) => !d)}
        accessibilityRole="button"
        testID="sky-details-toggle">
        <Text style={ui.link}>{details ? 'ซ่อนรายละเอียดโมเดล ▴' : 'รายละเอียดโมเดล ▾'}</Text>
      </Pressable>
      {details ? (
        <View style={styles.details} testID="sky-details">
          <Text style={styles.text} testID="sky-cloud">
            สัดส่วนเมฆ (ประมาณจากสีแดง/น้ำเงิน): {pct(v.cloudFraction)}
          </Text>
          {v.cloudFractionCnn !== null ? (
            <Text style={styles.small} testID="sky-cloud-cnn-clear-note">
              หมายเหตุ: {CLOUD_CLEAR_NOTE_TH}
            </Text>
          ) : null}
          {Object.entries(data.reliability).map(([k, t]) => (
            <Text key={k} style={styles.small}>
              {RELIABILITY_LABEL_TH[k] ?? k}: {t}
            </Text>
          ))}
        </View>
      ) : null}
      <Text style={styles.small} testID="sky-domain-gap">
        หมายเหตุ: {SKY_DOMAIN_GAP_TH}
      </Text>
    </>
  );
}

/** Camera: sky photo → /sky-image (supporting information only, never changes the UVI). */
export default function CameraScreen() {
  const { settings, ready, update } = useSettings();
  const [permission, requestPermission] = useCameraPermissions();
  const camera = useRef<CameraView>(null);
  const [shot, setShot] = useState<Shot>({ kind: 'idle' });
  const [forecast, setForecast] = useState<Forecast>({ kind: 'loading' });
  const gravity = useGravity();
  const elevation = gravity ? cameraElevationDeg(gravity, Platform.OS) : null;
  const hint = cameraAimHint(elevation);
  // angle at the moment of the shot (below 30°: still analysed, but labelled as unreliable)
  const elevationRef = useRef<number | null>(null);
  useEffect(() => {
    elevationRef.current = elevation;
  }, [elevation]);

  const takeAndAnalyze = useCallback(async () => {
    if (!camera.current) return;
    setShot({ kind: 'busy' });
    try {
      const elevationDeg = elevationRef.current;
      const photo = await camera.current.takePictureAsync({ quality: 0.8, exif: false });
      if (!photo) throw new Error('no photo');
      setShot({ kind: 'ok', data: await analyzeSkyPhoto(photo), elevationDeg });
      // cloud cover the UV model used for this hour, for the comparison card (extra information)
      setForecast({ kind: 'loading' });
      resolvePlace(settings)
        .then((p) => fetchForecast(p.lat, p.lon, 1))
        .then((fc) =>
          setForecast({
            kind: 'ok',
            cloudPct: fc.hours[0]?.cloud_cover ?? null,
          }),
        )
        .catch(() => setForecast({ kind: 'error' }));
    } catch (err) {
      setShot({
        kind: 'error',
        message: err instanceof ApiError ? err.message : 'ถ่ายหรือส่งภาพไม่สำเร็จ ลองใหม่อีกครั้ง',
        detail: err instanceof ApiError ? (err.detail ?? '') : describeError(err),
      });
    }
  }, [settings]);

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
        {shot.kind === 'ok' ? (
          <SkyResult data={shot.data} elevationDeg={shot.elevationDeg} forecast={forecast} />
        ) : null}
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
  content: {
    padding: 16,
    paddingBottom: 32,
    gap: 14,
    maxWidth: 680,
    width: '100%',
    alignSelf: 'center',
  },
  cameraBox: {
    borderRadius: 22,
    overflow: 'hidden',
    aspectRatio: 3 / 4,
    width: '100%',
  },
  camera: { flex: 1 },
  big: {
    color: colors.text,
    fontSize: 30,
    fontWeight: '700',
    letterSpacing: -0.5,
  },
  text: { color: colors.text, fontSize: 15 },
  small: { color: colors.muted, fontSize: 13 },
  gap4: { gap: 4 },
  gap8: { gap: 8 },
  bold: { fontWeight: '700' },
  body: { color: colors.text, fontSize: 16, lineHeight: 24 },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  track: {
    height: 8,
    borderRadius: 980,
    backgroundColor: colors.fill,
    overflow: 'hidden',
  },
  fill: { height: '100%', borderRadius: 980, backgroundColor: '#AEAEB2' },
  fillTop: { backgroundColor: colors.accent },
  overlay: { width: '100%', aspectRatio: 1, borderRadius: 18 },
  legend: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  swatch: {
    width: 14,
    height: 14,
    borderRadius: 4,
    backgroundColor: '#FF9F0A',
  },
  compareRow: { flexDirection: 'row', gap: 10 },
  cell: {
    flex: 1,
    backgroundColor: colors.background,
    borderRadius: 14,
    padding: 12,
    gap: 4,
  },
  cellValue: { color: colors.text, fontSize: 18, fontWeight: '700' },
  verdict: { fontSize: 22, fontWeight: '800' },
  details: {
    gap: 6,
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 14,
  },
  button: {
    alignSelf: 'flex-start',
    backgroundColor: colors.accent,
    borderRadius: 980,
    paddingHorizontal: 20,
    paddingVertical: 11,
  },
  disabled: { opacity: 0.5 },
  buttonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
  disclaimer: { color: colors.muted, fontSize: 12, textAlign: 'center', paddingVertical: 8 },
});
