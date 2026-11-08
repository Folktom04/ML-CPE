/**
 * Outdoor activity planner: which start time in the hourly forecast gives the smallest UV dose
 * for an activity of a given length.
 *
 * Uses the same dose rule as the "going out" card (`doseBetween`: alert_uvi, the upper value,
 * full sun assumed), so the fractions here match the sun session and the burn warning. Shade,
 * clothing, sunscreen and reflection from water or sand are not modelled.
 */

import type { HourUV } from '@/api/types';
import { BURN_FRACTION, doseBetween, hourStartMs } from '@/lib/dose';
import { MED_J_M2, type SkinType } from '@/lib/skinQuiz';

const HOUR_MS = 3600 * 1000;
/** Candidate start times are tried on this grid (local :00 and :30). */
export const STEP_MS = 30 * 60 * 1000;

export type Activity = {
  key: string;
  label: string;
  /** Default length in minutes when the activity is picked. */
  minutes: number;
  /** Extra hint for this activity, or null. */
  hint: string | null;
};

export const ACTIVITIES: Activity[] = [
  { key: 'run', label: 'วิ่ง/ออกกำลังกาย', minutes: 30, hint: null },
  { key: 'market', label: 'เดินตลาด', minutes: 60, hint: null },
  {
    key: 'swim',
    label: 'ว่ายน้ำ',
    minutes: 60,
    hint: 'น้ำสะท้อน UV และครีมกันแดดหลุดเร็ว ตัวเลขนี้ยังไม่ได้คิดแสงสะท้อน ควรใช้ครีมกันน้ำ',
  },
  { key: 'bike', label: 'ปั่นจักรยาน', minutes: 90, hint: null },
  {
    key: 'beach',
    label: 'เที่ยวทะเล/งานกลางแจ้ง',
    minutes: 120,
    hint: 'ทรายและน้ำสะท้อน UV เพิ่ม ตัวเลขจริงอาจสูงกว่านี้',
  },
];

export const DURATIONS = [30, 60, 90, 120] as const;

export type Slot = {
  startMs: number;
  endMs: number;
  /** Dose as a fraction of the MED of the skin type (1 = skin starts to redden). */
  fraction: number;
};

export type Plan = {
  /** Up to 3 non-overlapping slots with the smallest dose, earliest first among equals. The
   * first is always kept; the others only when below the 80 % warning. */
  best: Slot[];
  /** The slot with the largest dose, or null when there is no candidate. */
  worst: Slot | null;
  /** Starting right now, or null if it is dark now or the forecast does not cover it. */
  now: Slot | null;
};

export type Risk = 'low' | 'mid' | 'high';

/** Risk band of a dose fraction: below 50 % low, below the 80 % warning mid, else high. */
export function riskOf(fraction: number): Risk {
  if (fraction < 0.5) return 'low';
  if (fraction < BURN_FRACTION) return 'mid';
  return 'high';
}

/** WHO palette colours for the bands (green, orange, red). */
export const RISK_COLORS: Record<Risk, string> = {
  low: '#3E9B4F',
  mid: '#E36B12',
  high: '#D22F3A',
};

/** Thai advice for a band. */
export function riskAdvice(risk: Risk): string {
  if (risk === 'low') return 'เสี่ยงต่ำ ทาครีมกันแดดตามปกติก็พอ';
  if (risk === 'mid') return 'ควรทาครีม SPF 30+ สวมหมวกและแว่นกันแดด';
  return 'เสี่ยงผิวไหม้ ควรเลี่ยงช่วงนี้ หรือทาครีม SPF 50+ และอยู่ในร่มเป็นระยะ';
}

/** True when every forecast hour that the span touches is daylight (and the span is covered). */
function allDaylight(hours: HourUV[], fromMs: number, toMs: number): boolean {
  let touched = false;
  for (const h of hours) {
    const start = hourStartMs(h);
    if (start + HOUR_MS <= fromMs || start >= toMs) continue;
    if (!h.is_daylight) return false;
    touched = true;
  }
  return touched;
}

/** Slot for one start time, or null when it is not fully covered by daylight forecast hours. */
function slotAt(hours: HourUV[], skin: SkinType, startMs: number, lenMs: number): Slot | null {
  const endMs = startMs + lenMs;
  if (!allDaylight(hours, startMs, endMs)) return null;
  const dose = doseBetween(hours, startMs, endMs);
  if (dose === null) return null;
  return { startMs, endMs, fraction: dose / MED_J_M2[skin] };
}

/**
 * Plan an activity of `minutes` for skin type `skin` from `nowMs` on: tries every start on the
 * 30-minute grid inside the forecast, keeping only spans that lie in daylight hours.
 */
export function planActivity(
  hours: HourUV[],
  skin: SkinType,
  minutes: number,
  nowMs: number,
): Plan {
  const lenMs = minutes * 60 * 1000;
  const empty: Plan = { best: [], worst: null, now: null };
  if (hours.length === 0 || lenMs <= 0) return empty;

  const lastEnd = Math.max(...hours.map((h) => hourStartMs(h) + HOUR_MS));
  const slots: Slot[] = [];
  for (let t = Math.ceil(nowMs / STEP_MS) * STEP_MS; t + lenMs <= lastEnd; t += STEP_MS) {
    const s = slotAt(hours, skin, t, lenMs);
    if (s) slots.push(s);
  }

  const byDose = [...slots].sort((a, b) => a.fraction - b.fraction || a.startMs - b.startMs);
  const best: Slot[] = [];
  for (const s of byDose) {
    if (best.length === 3) break;
    // after the first slot, only slots below the 80 % warning count as "recommended"
    if (best.length > 0 && s.fraction >= BURN_FRACTION) break;
    if (best.every((b) => s.endMs <= b.startMs || s.startMs >= b.endMs)) best.push(s);
  }
  const worst = slots.length
    ? slots.reduce((w, s) => (s.fraction > w.fraction ? s : w), slots[0])
    : null;
  return { best, worst, now: slotAt(hours, skin, nowMs, lenMs) };
}
