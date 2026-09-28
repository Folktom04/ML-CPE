/**
 * Latest accelerometer reading (in g) while the screen is open (day 20). null on the web, on a
 * phone without an accelerometer, or before the first reading.
 */

import { Accelerometer } from 'expo-sensors';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

import type { Gravity } from '@/lib/orientation';

export const GRAVITY_INTERVAL_MS = 200;

export function useGravity(): Gravity | null {
  const [g, setG] = useState<Gravity | null>(null);

  useEffect(() => {
    if (Platform.OS === 'web') return;
    let sub: { remove: () => void } | null = null;
    let active = true;
    Accelerometer.isAvailableAsync()
      .then((ok) => {
        if (!ok || !active) return;
        Accelerometer.setUpdateInterval(GRAVITY_INTERVAL_MS);
        sub = Accelerometer.addListener(({ x, y, z }) => setG({ x, y, z }));
      })
      .catch(() => undefined);
    return () => {
      active = false;
      sub?.remove();
    };
  }, []);

  return g;
}
