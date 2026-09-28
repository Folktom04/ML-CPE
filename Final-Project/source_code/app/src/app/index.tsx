import { Link } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { ApiError, describeError, fetchForecast, fetchPredict } from '@/api/client';
import type { PredictResponse } from '@/api/types';
import { Card, colors, Note } from '@/components/Card';
import { HourlyChart } from '@/components/HourlyChart';
import { UVCard } from '@/components/UVCard';
import { UvaUvbCard } from '@/components/UvaUvbCard';
import { API_URL, DEFAULT_LOCATION, DEFAULT_SKIN_TYPE, DISCLAIMER_TH } from '@/config';
import { chartHours } from '@/lib/chart';
import { useSettings } from '@/lib/SettingsContext';
import { nextDaytimePeak, type DayPeak } from '@/lib/uv';

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; data: PredictResponse; nextPeak: DayPeak | null }
  | { kind: 'error'; message: string; url: string; detail: string };

/** At night: peak of the next daytime period from /forecast (null if unavailable). */
async function loadNextPeak(data: PredictResponse): Promise<DayPeak | null> {
  try {
    const fc = await fetchForecast(DEFAULT_LOCATION.lat, DEFAULT_LOCATION.lon, 36);
    return nextDaytimePeak(fc.hours, data.time);
  } catch {
    return null; // the forecast is extra information; the page still works without it
  }
}

/** Fetch /predict for the default location and the user's skin type, as a screen state. */
async function loadState(skinType: string): Promise<State> {
  try {
    const data = await fetchPredict({
      lat: DEFAULT_LOCATION.lat,
      lon: DEFAULT_LOCATION.lon,
      skin_type: skinType,
    });
    return { kind: 'ok', data, nextPeak: data.is_daylight ? null : await loadNextPeak(data) };
  } catch (err) {
    if (err instanceof ApiError) {
      return {
        kind: 'error',
        message: err.message,
        url: err.url ?? `${API_URL}/predict`,
        detail: err.detail ?? '',
      };
    }
    return {
      kind: 'error',
      message: 'เกิดข้อผิดพลาดที่ไม่คาดคิด',
      url: `${API_URL}/predict`,
      detail: describeError(err),
    };
  }
}

/** Home: UV now (level colour, range, q90 warning), hourly chart, UVA/UVB and burn time. */
export default function HomeScreen() {
  const { settings, ready } = useSettings();
  const skinType = settings.skinType ?? DEFAULT_SKIN_TYPE;
  // A result belongs to one skin type; after a change the screen shows "loading" until the
  // answer for the new type arrives.
  const [loaded, setLoaded] = useState<{ skin: string; state: State } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const state: State = loaded?.skin === skinType ? loaded.state : { kind: 'loading' };

  useEffect(() => {
    if (!ready) return; // wait for the stored skin type
    let active = true;
    loadState(skinType).then((s) => {
      if (active) setLoaded({ skin: skinType, state: s });
    });
    return () => {
      active = false;
    };
  }, [ready, skinType]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    setLoaded({ skin: skinType, state: await loadState(skinType) });
    setRefreshing(false);
  }, [skinType]);

  const retry = useCallback(async () => {
    setLoaded(null);
    setLoaded({ skin: skinType, state: await loadState(skinType) });
  }, [skinType]);

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <Text style={styles.place}>
        {DEFAULT_LOCATION.name} (ตำแหน่งเริ่มต้น) · ผิวประเภท {skinType}
      </Text>
      {ready && settings.skinType === null ? (
        <Link href="/quiz" asChild>
          <Pressable accessibilityRole="button" testID="quiz-prompt">
            <Note>ยังไม่ได้ระบุประเภทผิว ใช้ประเภท III ชั่วคราว · แตะเพื่อทำแบบสอบถาม 5 ข้อ</Note>
          </Pressable>
        </Link>
      ) : null}

      {state.kind === 'loading' ? (
        <View style={styles.center} testID="loading">
          <ActivityIndicator size="large" />
          <Text style={styles.muted}>กำลังประเมินค่า UV…</Text>
        </View>
      ) : null}

      {state.kind === 'error' ? (
        <Card title="โหลดข้อมูลไม่สำเร็จ">
          <Text style={styles.error} testID="error-message">
            {state.message}
          </Text>
          <Text style={styles.debug} testID="error-url" selectable>
            ที่อยู่ที่เรียก: {state.url}
          </Text>
          {state.detail ? (
            <Text style={styles.debug} testID="error-detail" selectable>
              รายละเอียด: {state.detail}
            </Text>
          ) : null}
          <Pressable style={styles.button} onPress={retry} accessibilityRole="button">
            <Text style={styles.buttonText}>ลองใหม่</Text>
          </Pressable>
        </Card>
      ) : null}

      {state.kind === 'ok' ? (
        <>
          <UVCard data={state.data} />
          <HourlyChart hours={chartHours(state.data)} isDaylight={state.data.is_daylight} />
          <UvaUvbCard data={state.data} nextPeak={state.nextPeak} />
        </>
      ) : null}

      <Text style={styles.disclaimer} testID="disclaimer">
        {state.kind === 'ok' ? state.data.disclaimer : DISCLAIMER_TH}
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 16, gap: 12, maxWidth: 640, width: '100%', alignSelf: 'center' },
  place: { color: colors.muted, fontSize: 14 },
  center: { alignItems: 'center', gap: 8, paddingVertical: 48 },
  muted: { color: colors.muted },
  error: { color: colors.text, fontSize: 15 },
  debug: {
    color: colors.muted,
    fontSize: 12,
    fontFamily: Platform.select({ ios: 'Menlo', default: 'monospace' }),
  },
  button: {
    alignSelf: 'flex-start',
    backgroundColor: colors.text,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  buttonText: { color: '#FFFFFF', fontWeight: '600' },
  disclaimer: { color: colors.muted, fontSize: 12, textAlign: 'center', paddingVertical: 8 },
});
