import {
  clearSettings,
  DEFAULT_SETTINGS,
  loadSettings,
  parseSettings,
  safeThresholdFor,
  saveSettings,
  serverSettings,
  STORAGE_KEY,
} from '@/lib/settings';

import { MemoryStorage } from './helpers';

it.each([
  [6, 4],
  [8, 6],
  [11, 9],
])('safe threshold follows the alert threshold: %p -> %p', (alert, safe) => {
  expect(safeThresholdFor(alert)).toBe(safe);
  expect(safe).toBeLessThan(alert); // same rule as the API / database
});

it('gives the defaults for nothing stored or unreadable JSON', () => {
  expect(parseSettings(null)).toEqual(DEFAULT_SETTINGS);
  expect(parseSettings('{not json')).toEqual(DEFAULT_SETTINGS);
  expect(parseSettings('[1,2]')).toEqual(DEFAULT_SETTINGS);
  expect(parseSettings('"text"')).toEqual(DEFAULT_SETTINGS);
  expect(DEFAULT_SETTINGS).toMatchObject({
    skinType: null,
    alertThreshold: 8,
    alertBurnMinutes: 30,
    serverConsent: false, // opt-in only
  });
  expect(parseSettings(JSON.stringify({ serverConsent: 'yes' })).serverConsent).toBe(false);
});

it('keeps valid fields and resets damaged ones one by one', () => {
  const s = parseSettings(
    JSON.stringify({
      skinType: 'IV',
      notifyEnabled: false,
      alertThreshold: 7, // not offered
      alertBurnMinutes: 60,
      dailySummary: 'yes', // wrong type
      deviceId: 'short',
      userId: 12,
    }),
  );
  expect(s).toEqual({
    ...DEFAULT_SETTINGS,
    skinType: 'IV',
    notifyEnabled: false,
    alertBurnMinutes: 60,
    userId: 12,
  });
  expect(parseSettings(JSON.stringify({ skinType: 'VII', userId: -1 }))).toEqual(DEFAULT_SETTINGS);
});

it('saves, loads and clears through the storage', async () => {
  const storage = new MemoryStorage();
  const s = { ...DEFAULT_SETTINGS, skinType: 'II' as const, alertThreshold: 11 as const };
  await saveSettings(storage, s);
  expect(await loadSettings(storage)).toEqual(s);
  await clearSettings(storage);
  expect(storage.data.has(STORAGE_KEY)).toBe(false);
  expect(await loadSettings(storage)).toEqual(DEFAULT_SETTINGS);
});

it('falls back to the defaults when storage fails', async () => {
  const storage = new MemoryStorage({ skinType: 'V' });
  storage.fail = true;
  expect(await loadSettings(storage)).toEqual(DEFAULT_SETTINGS);
});

it('maps the server fields to the API names (no local-only fields, no device id)', () => {
  const body = serverSettings({ ...DEFAULT_SETTINGS, skinType: 'III', deviceId: 'x'.repeat(20) });
  expect(body).toEqual({
    skin_type: 'III',
    notify_enabled: true,
    alert_threshold: 8,
    alert_burn_minutes: 30,
  });
});
