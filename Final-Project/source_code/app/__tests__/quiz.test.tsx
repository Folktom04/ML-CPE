import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { useRouter } from 'expo-router';

import { createUser } from '@/api/client';
import QuizScreen from '@/app/quiz';

import { MemoryStorage, renderWithSettings } from './helpers';

jest.mock('@/api/client', () => {
  const actual = jest.requireActual('@/api/client');
  return { ...actual, createUser: jest.fn(), updateUserSettings: jest.fn() };
});
const mockCreate = createUser as jest.MockedFunction<typeof createUser>;

beforeEach(() => {
  mockCreate.mockReset();
  mockCreate.mockRejectedValue(new Error('offline')); // the quiz must work without the server
  jest.mocked(useRouter().back).mockClear();
});

async function answer(scores: number[]) {
  for (const [q, s] of scores.entries()) {
    await fireEvent.press(screen.getByTestId(`q${q}-o${s}`));
  }
}

it('shows the result only when all 5 questions are answered', async () => {
  await renderWithSettings(<QuizScreen />);
  expect(screen.getByTestId('quiz-pending')).toBeTruthy();
  await answer([1, 1, 1, 1]);
  expect(screen.queryByTestId('quiz-result')).toBeNull();
  await answer([1, 1, 1, 1, 1]);
  expect(screen.getByTestId('quiz-result')).toHaveTextContent('ผิวประเภท II');
  expect(screen.getByTestId('quiz-score')).toHaveTextContent('คะแนน 5 จาก 20');
});

it('a boundary score goes to the lighter type and the result carries the caveat', async () => {
  await renderWithSettings(<QuizScreen />);
  await answer([2, 2, 1, 1, 1]); // 7: boundary of II / III
  expect(screen.getByTestId('quiz-result')).toHaveTextContent('ผิวประเภท II');
  await answer([4, 4, 2, 2, 2]); // 14: boundary of IV / V
  expect(screen.getByTestId('quiz-result')).toHaveTextContent('ผิวประเภท IV');
  expect(screen.getByTestId('quiz-note')).toHaveTextContent(
    /แบบย่อดัดแปลงจาก Fitzpatrick ยังไม่ผ่านการตรวจสอบทางวิชาการ/,
  );
});

it('saves the result in settings and goes back', async () => {
  const storage = new MemoryStorage();
  await renderWithSettings(<QuizScreen />, storage);
  await answer([4, 4, 4, 4, 4]);
  await fireEvent.press(screen.getByTestId('quiz-save'));
  await waitFor(() => expect(storage.stored()?.skinType).toBe('VI'));
  expect(useRouter().back).toHaveBeenCalled();
});

it('a type picked by hand overrides the score', async () => {
  const storage = new MemoryStorage();
  await renderWithSettings(<QuizScreen />, storage);
  await answer([0, 0, 0, 0, 0]);
  await fireEvent.press(screen.getByTestId('manual-IV'));
  expect(screen.getByTestId('quiz-result')).toHaveTextContent('ผิวประเภท IV');
  expect(screen.queryByTestId('quiz-score')).toBeNull();
  await fireEvent.press(screen.getByTestId('quiz-save'));
  await waitFor(() => expect(storage.stored()?.skinType).toBe('IV'));
});
