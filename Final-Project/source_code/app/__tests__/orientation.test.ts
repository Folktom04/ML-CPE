import {
  cameraAimHint,
  cameraElevationDeg,
  faceUpMessage,
  faceUpStatus,
  screenTiltDeg,
  upZ,
} from '@/lib/orientation';

const rad = (d: number) => (d * Math.PI) / 180;

it('face up is 0°, upright 90°, face down 180° on Android (z = +1 g face up)', () => {
  expect(screenTiltDeg({ x: 0, y: 0, z: 1 }, 'android')).toBeCloseTo(0);
  expect(screenTiltDeg({ x: 0, y: 1, z: 0 }, 'android')).toBeCloseTo(90);
  expect(screenTiltDeg({ x: 0, y: 0, z: -1 }, 'android')).toBeCloseTo(180);
});

it('iOS reports the opposite z sign and is flipped', () => {
  expect(upZ({ x: 0, y: 0, z: -1 }, 'ios')).toBe(1);
  expect(screenTiltDeg({ x: 0, y: 0, z: -1 }, 'ios')).toBeCloseTo(0);
  expect(screenTiltDeg({ x: 0, y: 0, z: 1 }, 'ios')).toBeCloseTo(180);
});

it('tilt does not depend on |g| (shaking scales the vector)', () => {
  const g = { x: 0, y: Math.sin(rad(30)), z: Math.cos(rad(30)) };
  expect(screenTiltDeg(g, 'android')).toBeCloseTo(30);
  expect(screenTiltDeg({ x: 0, y: 2 * g.y, z: 2 * g.z }, 'android')).toBeCloseTo(30);
});

it('no reading when |g| is ~0 or not a number', () => {
  expect(screenTiltDeg({ x: 0, y: 0, z: 0 }, 'android')).toBeNull();
  expect(screenTiltDeg({ x: NaN, y: 0, z: 1 }, 'android')).toBeNull();
  expect(faceUpStatus(null)).toBe('unknown');
  expect(faceUpMessage('unknown', null)).toBe('ยังอ่านทิศทางมือถือไม่ได้');
});

it.each([
  [0, 'face_up'],
  [15, 'face_up'],
  [15.1, 'tilted'],
  [89, 'tilted'],
  [90, 'face_down'],
  [180, 'face_down'],
])('tilt %p° → %p', (deg, status) => {
  expect(faceUpStatus(deg)).toBe(status);
});

it('Thai messages name the tilt', () => {
  expect(faceUpMessage('face_up', 4.4)).toBe('ทิศทางถูกต้อง: หน้าจอหงายขึ้นฟ้า (เอียง 4°)');
  expect(faceUpMessage('tilted', 30)).toContain('เอียงเกินไป (เอียง 30°)');
  expect(faceUpMessage('face_down', 170)).toContain('ต้องหงายขึ้นฟ้า');
});

it('back camera points at the zenith when the screen faces down', () => {
  expect(cameraElevationDeg({ x: 0, y: 0, z: -1 }, 'android')).toBeCloseTo(90);
  expect(cameraElevationDeg({ x: 0, y: 1, z: 0 }, 'android')).toBeCloseTo(0); // upright: horizon
  expect(cameraElevationDeg({ x: 0, y: 0, z: 1 }, 'ios')).toBeCloseTo(90);
  expect(cameraAimHint(10)).toContain('ยกกล้องขึ้นอีก');
  expect(cameraAimHint(30)).toBeNull();
  expect(cameraAimHint(null)).toBeNull();
});
