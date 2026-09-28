/**
 * Phone orientation from the accelerometer (day 20).
 *
 * At rest the accelerometer measures the reaction to gravity, i.e. a vector that points UP in
 * the phone's frame (x right, y towards the top edge, z out of the screen). expo-sensors reports
 * it in g. Android passes the sensor through (screen facing up → z ≈ +1); iOS passes CoreMotion
 * through, whose sign is the opposite (screen facing up → z ≈ −1), so iOS values are flipped
 * here. The Android sign was read from expo-sensors' AccelerometerModule.kt; check it on a
 * real phone (app README, day 20 checklist).
 */

export type Gravity = { x: number; y: number; z: number };

/** Largest tilt of the screen from "facing straight up" that still counts as face up. */
export const FACE_UP_MAX_TILT_DEG = 15;

/** Smallest angle of the back camera above the horizon for a sky photo. */
export const CAMERA_MIN_ELEVATION_DEG = 30;

const DEG = 180 / Math.PI;

/** z component that is +1 g when the screen faces straight up, on both platforms. */
export function upZ(g: Gravity, platform: string): number {
  return platform === 'ios' ? -g.z : g.z;
}

function norm(g: Gravity): number {
  return Math.hypot(g.x, g.y, g.z);
}

/**
 * Angle (degrees, 0-180) between the screen's normal and straight up: 0 = lying face up,
 * 90 = standing upright, 180 = face down. null when there is no usable reading (|g| ≈ 0).
 */
export function screenTiltDeg(g: Gravity, platform: string): number | null {
  const n = norm(g);
  if (!Number.isFinite(n) || n < 0.1) return null;
  const c = Math.min(1, Math.max(-1, upZ(g, platform) / n));
  return Math.acos(c) * DEG;
}

/**
 * Elevation (degrees, −90…90) of the back camera's view above the horizon. The back camera
 * looks out of the back (−z), so it points at the zenith (90) when the screen faces down.
 */
export function cameraElevationDeg(g: Gravity, platform: string): number | null {
  const tilt = screenTiltDeg(g, platform);
  return tilt === null ? null : tilt - 90;
}

export type FaceUpStatus = 'face_up' | 'tilted' | 'face_down' | 'unknown';

/** Is the light sensor (front, next to the screen) facing the sky? */
export function faceUpStatus(tiltDeg: number | null): FaceUpStatus {
  if (tiltDeg === null) return 'unknown';
  if (tiltDeg <= FACE_UP_MAX_TILT_DEG) return 'face_up';
  if (tiltDeg >= 90) return 'face_down';
  return 'tilted';
}

/** Thai text for the light-sensor orientation status. */
export function faceUpMessage(status: FaceUpStatus, tiltDeg: number | null): string {
  const deg = tiltDeg === null ? '' : ` (เอียง ${Math.round(tiltDeg)}°)`;
  switch (status) {
    case 'face_up':
      return `ทิศทางถูกต้อง: หน้าจอหงายขึ้นฟ้า${deg}`;
    case 'tilted':
      return `เอียงเกินไป${deg} วางมือถือให้หน้าจอหงายขึ้นฟ้า (เอียงไม่เกิน ${FACE_UP_MAX_TILT_DEG}°)`;
    case 'face_down':
      return `หน้าจอคว่ำหรือตั้งอยู่${deg} เซนเซอร์แสงอยู่ด้านหน้าจอ ต้องหงายขึ้นฟ้า`;
    default:
      return 'ยังอ่านทิศทางมือถือไม่ได้';
  }
}

/** Thai hint for aiming the back camera at the sky (null when the aim is fine). */
export function cameraAimHint(elevationDeg: number | null): string | null {
  if (elevationDeg === null) return null;
  if (elevationDeg < CAMERA_MIN_ELEVATION_DEG) {
    return `ยกกล้องขึ้นอีก ให้เห็นแต่ท้องฟ้า (ตอนนี้เงย ${Math.round(elevationDeg)}° ควรเกิน ${CAMERA_MIN_ELEVATION_DEG}°)`;
  }
  return null;
}
