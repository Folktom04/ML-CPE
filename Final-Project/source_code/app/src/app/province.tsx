import { useRouter } from 'expo-router';
import { useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { colors } from '@/components/Card';
import { searchProvinces } from '@/lib/provinces';
import { useSettings } from '@/lib/SettingsContext';

/** Pick a province by hand (used when location permission is denied, or by choice). */
export default function ProvinceScreen() {
  const router = useRouter();
  const { settings, update } = useSettings();
  const [query, setQuery] = useState('');
  const results = searchProvinces(query);

  const choose = async (nameTh: string) => {
    await update({ locationMode: 'province', province: nameTh });
    if (router.canGoBack()) router.back();
    else router.replace('/');
  };

  return (
    <View style={styles.screen}>
      <TextInput
        value={query}
        onChangeText={setQuery}
        placeholder="ค้นหาจังหวัด เช่น เชียงใหม่ หรือ Chiang Mai"
        style={styles.search}
        autoCorrect={false}
        accessibilityLabel="ค้นหาจังหวัด"
        testID="province-search"
      />
      <Text style={styles.hint}>ใช้พิกัดตัวเมืองของจังหวัดที่เลือกในการคำนวณค่า UV</Text>
      <FlatList
        data={results}
        keyExtractor={(p) => p.name_th}
        keyboardShouldPersistTaps="handled"
        initialNumToRender={20}
        ListEmptyComponent={<Text style={styles.hint}>ไม่พบจังหวัดที่ค้นหา</Text>}
        renderItem={({ item }) => {
          const on = settings.locationMode === 'province' && settings.province === item.name_th;
          return (
            <Pressable
              onPress={() => choose(item.name_th)}
              style={[styles.row, on && styles.rowOn]}
              accessibilityRole="button"
              accessibilityState={{ selected: on }}
              testID={`province-${item.name_en}`}>
              <Text style={styles.name}>{item.name_th}</Text>
              <Text style={styles.en}>{item.name_en}</Text>
            </Pressable>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background, padding: 16, gap: 8 },
  search: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: colors.text,
  },
  hint: { color: colors.muted, fontSize: 13 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rowOn: { backgroundColor: '#EEF2F6' },
  name: { color: colors.text, fontSize: 16 },
  en: { color: colors.muted, fontSize: 13 },
});
