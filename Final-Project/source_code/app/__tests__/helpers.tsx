import { render } from '@testing-library/react-native';
import type { ReactElement } from 'react';

import { SettingsProvider } from '@/lib/SettingsContext';
import { STORAGE_KEY, type KeyValueStorage, type Settings } from '@/lib/settings';

/** In-memory storage with the AsyncStorage interface; `fail` makes every call reject. */
export class MemoryStorage implements KeyValueStorage {
  data = new Map<string, string>();
  fail = false;

  constructor(initial?: Partial<Settings>) {
    if (initial) this.data.set(STORAGE_KEY, JSON.stringify(initial));
  }

  async getItem(key: string) {
    if (this.fail) throw new Error('storage broken');
    return this.data.get(key) ?? null;
  }

  async setItem(key: string, value: string) {
    if (this.fail) throw new Error('storage broken');
    this.data.set(key, value);
  }

  async removeItem(key: string) {
    if (this.fail) throw new Error('storage broken');
    this.data.delete(key);
  }

  /** Parsed stored settings (or null). */
  stored(): Settings | null {
    const raw = this.data.get(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  }
}

export const DEVICE = '11111111-2222-4333-8444-555555555555';

/** Render `ui` inside a SettingsProvider backed by `storage`. */
export function renderWithSettings(ui: ReactElement, storage = new MemoryStorage()) {
  return render(
    <SettingsProvider storage={storage} newDeviceId={() => DEVICE}>
      {ui}
    </SettingsProvider>,
  );
}
