import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Card, colors, Note } from '@/components/Card';
import { useSettings } from '@/lib/SettingsContext';
import {
  burnMinutesAt,
  MAX_SCORE,
  MED_J_M2,
  QUESTIONS,
  QUIZ_NOTE_TH,
  scoreToSkinType,
  SKIN_DESCRIPTION_TH,
  SKIN_TYPES,
  totalScore,
  type SkinType,
} from '@/lib/skinQuiz';

/** Five-question skin-type quiz; the result (or a type picked by hand) is saved in settings. */
export default function QuizScreen() {
  const router = useRouter();
  const { update } = useSettings();
  const [answers, setAnswers] = useState<(number | null)[]>(QUESTIONS.map(() => null));
  const [manual, setManual] = useState<SkinType | null>(null);

  const complete = answers.every((a) => a !== null);
  const score = complete ? totalScore(answers) : null;
  const result: SkinType | null = manual ?? (score !== null ? scoreToSkinType(score) : null);

  const choose = (q: number, option: number) => {
    setManual(null);
    setAnswers((prev) => prev.map((a, i) => (i === q ? option : a)));
  };

  const save = async () => {
    if (!result) return;
    await update({ skinType: result });
    if (router.canGoBack()) router.back();
    else router.replace('/');
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.muted}>
        ตอบ 5 ข้อเพื่อประมาณประเภทผิว ใช้คำนวณเวลาก่อนผิวไหม้และระดับการเตือน
      </Text>

      {QUESTIONS.map((q, qi) => (
        <Card key={q.id} title={`ข้อ ${qi + 1} จาก ${QUESTIONS.length}`}>
          <Text style={styles.question}>{q.text}</Text>
          {q.options.map((opt, oi) => {
            const on = answers[qi] === oi;
            return (
              <Pressable
                key={opt}
                onPress={() => choose(qi, oi)}
                style={[styles.option, on && styles.optionOn]}
                accessibilityRole="radio"
                accessibilityState={{ checked: on }}
                testID={`q${qi}-o${oi}`}>
                <View style={[styles.radio, on && styles.radioOn]} />
                <Text style={styles.optionText}>{opt}</Text>
              </Pressable>
            );
          })}
        </Card>
      ))}

      <Card title="หรือเลือกประเภทผิวเอง">
        <View style={styles.chips}>
          {SKIN_TYPES.map((t) => (
            <Pressable
              key={t}
              onPress={() => setManual(t)}
              style={[styles.chip, manual === t && styles.chipOn]}
              accessibilityRole="radio"
              accessibilityState={{ checked: manual === t }}
              testID={`manual-${t}`}>
              <Text style={[styles.chipText, manual === t && styles.chipTextOn]}>{t}</Text>
            </Pressable>
          ))}
        </View>
      </Card>

      {result ? (
        <Card title="ผลประเมิน">
          <Text style={styles.result} testID="quiz-result">
            ผิวประเภท {result}
          </Text>
          <Text style={styles.text}>{SKIN_DESCRIPTION_TH[result]}</Text>
          {manual === null && score !== null ? (
            <Text style={styles.muted} testID="quiz-score">
              คะแนน {score} จาก {MAX_SCORE}
            </Text>
          ) : (
            <Text style={styles.muted}>เลือกเอง</Text>
          )}
          <Text style={styles.muted}>
            ปริมาณ UV ที่ทำให้ผิวแดง (MED) {MED_J_M2[result]} J/m² · ที่ UVI 10 ผิวจะเริ่มไหม้ในราว{' '}
            {burnMinutesAt(result, 10)} นาที
          </Text>
          <Note testID="quiz-note">{QUIZ_NOTE_TH}</Note>
          <Pressable
            style={styles.button}
            onPress={save}
            accessibilityRole="button"
            testID="quiz-save">
            <Text style={styles.buttonText}>ใช้ประเภทผิวนี้</Text>
          </Pressable>
        </Card>
      ) : (
        <Text style={styles.muted} testID="quiz-pending">
          ตอบให้ครบ 5 ข้อ หรือเลือกประเภทเอง เพื่อดูผล
        </Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: 16, paddingBottom: 32, gap: 14, maxWidth: 680, width: '100%', alignSelf: 'center' },
  question: { color: colors.text, fontSize: 19, fontWeight: '700', letterSpacing: -0.2 },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 13,
    paddingHorizontal: 14,
    borderRadius: 14,
    backgroundColor: colors.background,
    borderWidth: 1.5,
    borderColor: colors.background,
  },
  optionOn: { borderColor: colors.accent, backgroundColor: '#EAF3FE' },
  radio: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: '#C7C7CC' },
  radioOn: { borderColor: colors.accent, borderWidth: 6 },
  optionText: { color: colors.text, fontSize: 15, flexShrink: 1 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', backgroundColor: colors.fill, borderRadius: 10, padding: 2, gap: 2 },
  chip: { minWidth: 48, alignItems: 'center', paddingVertical: 7, paddingHorizontal: 12, borderRadius: 8 },
  chipOn: { backgroundColor: colors.card, boxShadow: '0 1px 3px rgba(0,0,0,0.12)' },
  chipText: { color: colors.text, fontWeight: '500' },
  chipTextOn: { fontWeight: '700' },
  result: { color: colors.text, fontSize: 34, fontWeight: '700', letterSpacing: -0.6 },
  text: { color: colors.text, fontSize: 15 },
  muted: { color: colors.muted, fontSize: 13 },
  button: {
    alignSelf: 'flex-start',
    backgroundColor: colors.accent,
    borderRadius: 980,
    paddingHorizontal: 20,
    paddingVertical: 11,
  },
  buttonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
});
