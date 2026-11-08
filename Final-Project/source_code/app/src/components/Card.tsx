import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

/**
 * Design tokens (Apple-web style, day 30+ redesign): light grey page, white cards without
 * borders, near-black text, Apple blue for actions. UV levels keep the WHO palette (`lib/uv`).
 */
export const colors = {
  background: '#F5F5F7',
  card: '#FFFFFF',
  text: '#1D1D1F',
  muted: '#6E6E73',
  border: '#E5E5EA',
  /** Grey track of segmented controls and secondary buttons. */
  fill: '#E8E8ED',
  /** Apple blue: buttons and links. */
  accent: '#0071E3',
  noteBg: '#FFF4E0',
  noteText: '#8A5300',
};

/** Section in the Apple-web style: a large headline above a white rounded card. */
export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <View style={styles.section}>
      {title ? <Text style={styles.title}>{title}</Text> : null}
      <View style={styles.card}>{children}</View>
    </View>
  );
}

/** Small rounded note (data quality, location warnings). */
export function Note({ children, testID }: { children: ReactNode; testID?: string }) {
  return (
    <Text style={styles.note} testID={testID}>
      {children}
    </Text>
  );
}

/** Shared control styles, so every screen has the same buttons and chips. */
export const ui = StyleSheet.create({
  /** Filled blue pill: the main action. */
  button: {
    alignSelf: 'flex-start',
    backgroundColor: colors.accent,
    borderRadius: 980,
    paddingHorizontal: 20,
    paddingVertical: 11,
  },
  buttonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
  /** Blue outline pill: a second action. */
  outline: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: colors.accent,
    borderRadius: 980,
    paddingHorizontal: 18,
    paddingVertical: 9,
  },
  outlineText: { color: colors.accent, fontSize: 16, fontWeight: '500' },
  /** Plain blue text link. */
  link: { color: colors.accent, fontSize: 16, fontWeight: '500' },
  /** Grey pill: neutral choices. */
  soft: {
    alignSelf: 'flex-start',
    backgroundColor: colors.fill,
    borderRadius: 980,
    paddingHorizontal: 18,
    paddingVertical: 10,
  },
  softText: { color: colors.text, fontSize: 15, fontWeight: '500' },
  /** Segmented control (iOS): grey track, white selected segment. */
  segTrack: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    backgroundColor: colors.fill,
    borderRadius: 10,
    padding: 2,
    gap: 2,
  },
  seg: { borderRadius: 8, paddingHorizontal: 12, paddingVertical: 7 },
  segOn: { backgroundColor: colors.card, boxShadow: '0 1px 3px rgba(0,0,0,0.12)' },
  segText: { color: colors.text, fontSize: 13, fontWeight: '500' },
  segTextOn: { fontWeight: '700' },
  /** Small grey label above a value. */
  eyebrow: { color: colors.muted, fontSize: 13, fontWeight: '600', letterSpacing: 0.2 },
  /** Screen headline, e.g. on onboarding. */
  headline: { color: colors.text, fontSize: 30, fontWeight: '700', letterSpacing: -0.5 },
  body: { color: colors.text, fontSize: 16, lineHeight: 23 },
  hint: { color: colors.muted, fontSize: 13, lineHeight: 18 },
});

const styles = StyleSheet.create({
  section: { gap: 12, marginTop: 14 },
  card: {
    backgroundColor: colors.card,
    borderRadius: 22,
    padding: 22,
    gap: 10,
    boxShadow: '0 2px 14px rgba(0,0,0,0.05)',
  },
  title: {
    fontSize: 30,
    lineHeight: 38,
    fontWeight: '800',
    color: colors.text,
    letterSpacing: -0.8,
    paddingHorizontal: 4,
  },
  note: {
    backgroundColor: colors.noteBg,
    color: colors.noteText,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 13,
    lineHeight: 18,
    overflow: 'hidden',
  },
});
