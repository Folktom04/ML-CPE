/**
 * EAS Build runs `npm ci` on Linux with an npm older than ours (11.6.2). That npm expects the
 * peer deps of the optional `@napi-rs/wasm-runtime` (eslint-config-expo → … → unrs-resolver) at
 * the top level and stops with "package.json and package-lock.json are not in sync" when they are
 * missing. npm 11.6.2 drops them on `npm install`, so they were added by hand on day 24.
 * Check before a build: npx -y npm@10.9.2 ci --dry-run --ignore-scripts --os=linux --cpu=x64
 */
import lock from '../package-lock.json';

const packages = (lock as { packages: Record<string, { version?: string }> }).packages;

it.each(['node_modules/@emnapi/core', 'node_modules/@emnapi/runtime'])(
  'package-lock.json keeps %s for npm ci on EAS',
  (key) => {
    expect(packages[key]?.version).toMatch(/^1\./);
  },
);
