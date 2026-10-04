/**
 * The current time for screens that show live values (day 22 card, fixed after the field test of
 * 4 Oct 2026). JS timers pause while the phone is locked or the app is in the background, so an
 * interval alone left the "อยู่กลางแจ้ง" card showing the dose of its last tick before locking
 * (79 % instead of 87 %). The clock is therefore also refreshed as soon as the app becomes active.
 */

import { useEffect, useState } from 'react';
import { AppState } from 'react-native';

/** Refresh interval while the app is open. */
export const NOW_INTERVAL_MS = 30 * 1000;

const HOUR_MS = 3600 * 1000;

/**
 * Index of the clock hour of `ms`. Bangkok is UTC+7 (whole hours, no daylight saving), so its
 * hours start on UTC hours and epoch hours can be compared directly.
 */
export function clockHour(ms: number): number {
  return Math.floor(ms / HOUR_MS);
}

/** Whether `toMs` lies in a later clock hour than `fromMs`. */
export function hourChanged(fromMs: number, toMs: number): boolean {
  return clockHour(toMs) > clockHour(fromMs);
}

/**
 * Current time in ms, refreshed every `intervalMs` and whenever the app comes back to the
 * foreground. With `fixedMs` (tests) it returns that value and starts no timer or listener.
 */
export function useNow(intervalMs: number = NOW_INTERVAL_MS, fixedMs?: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (fixedMs !== undefined) return;
    const tick = () => setNow(Date.now());
    const id = setInterval(tick, intervalMs);
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') tick();
    });
    return () => {
      clearInterval(id);
      sub.remove();
    };
  }, [intervalMs, fixedMs]);
  return fixedMs ?? now;
}
