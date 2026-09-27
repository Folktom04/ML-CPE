import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

export const colors = {
  background: '#F4F6F8',
  card: '#FFFFFF',
  text: '#1F2933',
  muted: '#5F6B7A',
  border: '#E2E8F0',
  noteBg: '#FFF7E0',
  noteText: '#7A5B00',
};

/** White rounded card with an optional title. */
export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <View style={styles.card}>
      {title ? <Text style={styles.title}>{title}</Text> : null}
      {children}
    </View>
  );
}

/** Small yellow note line (data quality, location warnings). */
export function Note({ children, testID }: { children: ReactNode; testID?: string }) {
  return (
    <Text style={styles.note} testID={testID}>
      {children}
    </Text>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 16,
    gap: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  title: { fontSize: 15, fontWeight: '600', color: colors.muted },
  note: {
    backgroundColor: colors.noteBg,
    color: colors.noteText,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    fontSize: 13,
  },
});
