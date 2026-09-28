import { Link, Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Pressable, StyleSheet, Text } from 'react-native';

import { colors } from '@/components/Card';
import { SettingsProvider } from '@/lib/SettingsContext';

function SettingsLink() {
  return (
    <Link href="/settings" asChild>
      <Pressable accessibilityRole="button" hitSlop={8} testID="header-settings">
        <Text style={styles.headerLink}>ตั้งค่า</Text>
      </Pressable>
    </Link>
  );
}

export default function RootLayout() {
  return (
    <SettingsProvider>
      <Stack
        screenOptions={{
          headerTitleAlign: 'center',
          contentStyle: { backgroundColor: colors.background },
        }}>
        <Stack.Screen
          name="index"
          options={{ title: 'UV Guard', headerRight: () => <SettingsLink /> }}
        />
        <Stack.Screen name="settings" options={{ title: 'ตั้งค่า' }} />
        <Stack.Screen name="quiz" options={{ title: 'แบบสอบถามประเภทผิว' }} />
      </Stack>
      <StatusBar style="dark" />
    </SettingsProvider>
  );
}

const styles = StyleSheet.create({
  headerLink: { color: colors.text, fontSize: 16, fontWeight: '600', paddingHorizontal: 8 },
});
