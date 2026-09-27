import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { colors } from '@/components/Card';

export default function RootLayout() {
  return (
    <>
      <Stack
        screenOptions={{
          headerTitleAlign: 'center',
          contentStyle: { backgroundColor: colors.background },
        }}>
        <Stack.Screen name="index" options={{ title: 'UV Guard' }} />
      </Stack>
      <StatusBar style="dark" />
    </>
  );
}
