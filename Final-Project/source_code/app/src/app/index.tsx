import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { ApiError, fetchPredict } from '@/api/client';
import type { PredictResponse } from '@/api/types';
import { Card, colors } from '@/components/Card';
import { UVCard } from '@/components/UVCard';
import { UvaUvbCard } from '@/components/UvaUvbCard';
import { DEFAULT_LOCATION, DEFAULT_SKIN_TYPE, DISCLAIMER_TH } from '@/config';

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; data: PredictResponse }
  | { kind: 'error'; message: string };

/** Fetch /predict for the default location and skin type, as a screen state. */
async function loadState(): Promise<State> {
  try {
    const data = await fetchPredict({
      lat: DEFAULT_LOCATION.lat,
      lon: DEFAULT_LOCATION.lon,
      skin_type: DEFAULT_SKIN_TYPE,
    });
    return { kind: 'ok', data };
  } catch (err) {
    const message = err instanceof ApiError ? err.message : 'เกิดข้อผิดพลาดที่ไม่คาดคิด';
    return { kind: 'error', message };
  }
}

/** Home: UV now (level colour, range, q90 warning) + UVA/UVB and burn time. */
export default function HomeScreen() {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    let active = true;
    loadState().then((s) => {
      if (active) setState(s);
    });
    return () => {
      active = false;
    };
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    setState(await loadState());
    setRefreshing(false);
  }, []);

  const retry = useCallback(async () => {
    setState({ kind: 'loading' });
    setState(await loadState());
  }, []);

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
      <Text style={styles.place}>
        {DEFAULT_LOCATION.name} (ตำแหน่งเริ่มต้น) · ผิวประเภท {DEFAULT_SKIN_TYPE}
      </Text>

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
          <Pressable style={styles.button} onPress={retry} accessibilityRole="button">
            <Text style={styles.buttonText}>ลองใหม่</Text>
          </Pressable>
        </Card>
      ) : null}

      {state.kind === 'ok' ? (
        <>
          <UVCard data={state.data} />
          <UvaUvbCard data={state.data} />
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
