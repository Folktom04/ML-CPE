import { Link, Redirect } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
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
import { SunSessionCard } from '@/components/SunSessionCard';
import { UVCard } from '@/components/UVCard';
import { UvaUvbCard } from '@/components/UvaUvbCard';
import { API_URL, DEFAULT_SKIN_TYPE, DISCLAIMER_TH } from '@/config';
import { chartHours } from '@/lib/chart';
import { resolvePlace, type Place } from '@/lib/location';
import { useSettings } from '@/lib/SettingsContext';
import type { SkinType } from '@/lib/skinQuiz';
import { useLocalNotifications } from '@/lib/useLocalNotifications';
import { nextDaytimePeak, type DayPeak } from '@/lib/uv';

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; data: PredictResponse; nextPeak: DayPeak | null }
  | { kind: 'error'; message: string; url: string; detail: string };

/** At night: peak of the next daytime period from /forecast (null if unavailable). */
async function loadNextPeak(data: PredictResponse, place: Place): Promise<DayPeak | null> {
  try {
    const fc = await fetchForecast(place.lat, place.lon, 36);
    return nextDaytimePeak(fc.hours, data.time);
  } catch {
    return null; // the forecast is extra information; the page still works without it
  }
}

/** Fetch /predict for a place and the user's skin type, as a screen state. */
async function loadState(skinType: string, place: Place): Promise<State> {
  try {
    const data = await fetchPredict({ lat: place.lat, lon: place.lon, skin_type: skinType });
    return {
      kind: 'ok',
      data,
      nextPeak: data.is_daylight ? null : await loadNextPeak(data, place),
    };
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

/**
 * Home: UV now (level colour, range, q90 warning), hourly chart, UVA/UVB and burn time, for the
 * GPS position or the chosen province. Sends first-time users to the onboarding flow.
 */
export default function HomeScreen() {
  const { settings, ready, update, pushActive } = useSettings();
  const skinType = settings.skinType ?? DEFAULT_SKIN_TYPE;
  // A result belongs to one skin type and one location choice; after a change the screen shows
  // "loading" until the new answer arrives. In GPS mode the key does not include the province,
  // because the province is updated from the GPS fix itself.
  const key = `${skinType}|${
    settings.locationMode === 'gps' ? 'gps' : `${settings.locationMode}|${settings.province}`
  }`;
  const [loaded, setLoaded] = useState<{ key: string; place: Place; state: State } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const state: State = loaded?.key === key ? loaded.state : { kind: 'loading' };
  const place = loaded?.key === key ? loaded.place : null;
  const okData = state.kind === 'ok' ? state.data : null;
  // now + forecast hours; memoised so notifications are re-planned only for a new forecast
  const hours = useMemo(() => (okData ? chartHours(okData) : null), [okData]);
  useLocalNotifications(hours, settings, pushActive);

  const load = useCallback(async () => {
    const p = await resolvePlace(settings);
    const s = await loadState(skinType, p);
    // keep the nearest province of a GPS fix (sent to the server only with consent)
    if (p.source === 'gps' && p.province !== settings.province) {
      await update({ province: p.province });
    }
    return { key, place: p, state: s };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `key` covers the settings used
  }, [key]);

  useEffect(() => {
    if (!ready || !settings.onboarded) return; // wait for the stored settings
    let active = true;
    load().then((r) => {
      if (active) setLoaded(r);
    });
    return () => {
      active = false;
    };
  }, [ready, settings.onboarded, load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    setLoaded(await load());
    setRefreshing(false);
  }, [load]);

  const retry = useCallback(async () => {
    setLoaded(null);
    setLoaded(await load());
  }, [load]);

  if (ready && !settings.onboarded) return <Redirect href="/onboarding" />;

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <Text style={styles.place} testID="place-label">
        {place ? place.label : 'กำลังหาตำแหน่ง…'} · ผิวประเภท {skinType}
      </Text>
      {place?.notice ? <Note testID="place-notice">{place.notice}</Note> : null}
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
          <HourlyChart hours={hours ?? []} isDaylight={state.data.is_daylight} />
          <SunSessionCard
            hours={hours ?? []}
            skin={skinType as SkinType}
            isDaylight={state.data.is_daylight}
          />
          <UvaUvbCard data={state.data} nextPeak={state.nextPeak} />
        </>
      ) : null}

      <Card title="ดูเพิ่มเติม (ข้อมูลประกอบ ไม่เปลี่ยนค่า UVI)">
        <View style={styles.row}>
          <Link href="/camera" asChild>
            <Pressable style={styles.button} accessibilityRole="button" testID="open-camera">
              <Text style={styles.buttonText}>ถ่ายท้องฟ้า</Text>
            </Pressable>
          </Link>
          {Platform.OS === 'android' ? (
            <Link href="/light" asChild>
              <Pressable style={styles.button} accessibilityRole="button" testID="open-light">
                <Text style={styles.buttonText}>วัดแสง</Text>
              </Pressable>
            </Link>
          ) : null}
        </View>
      </Card>

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
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  disclaimer: { color: colors.muted, fontSize: 12, textAlign: 'center', paddingVertical: 8 },
});
