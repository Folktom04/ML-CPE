/**
 * Sky photo pipeline (day 20): re-encode → upload → delete every temporary file.
 *
 * The camera is asked for no EXIF (`exif: false`), and the photo is ALWAYS re-encoded by
 * expo-image-manipulator before upload: Android `Bitmap.compress` and iOS `jpegData` write
 * pixels only, so no GPS / time / phone model can leave the phone even if a camera still
 * embedded some. Deletion happens in `finally`, so it also runs when the upload fails.
 */

import { File } from 'expo-file-system';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';

import { uploadSkyImage } from '@/api/client';
import type { SkyImageResponse } from '@/api/types';
import { UPLOAD_JPEG_QUALITY, UPLOAD_MAX_SIDE } from '@/lib/sky';

export type Photo = { uri: string; width: number; height: number };

/** Resize so the longest side is at most UPLOAD_MAX_SIDE and save a fresh JPEG (no EXIF). */
export async function reencodePhoto(photo: Photo): Promise<string> {
  const ctx = ImageManipulator.manipulate(photo.uri);
  const longest = Math.max(photo.width, photo.height);
  if (longest > UPLOAD_MAX_SIDE) {
    ctx.resize(
      photo.width >= photo.height ? { width: UPLOAD_MAX_SIDE } : { height: UPLOAD_MAX_SIDE },
    );
  }
  const image = await ctx.renderAsync();
  const saved = await image.saveAsync({ compress: UPLOAD_JPEG_QUALITY, format: SaveFormat.JPEG });
  return saved.uri;
}

/**
 * Delete a temporary local file; never throws (a failed delete must not hide the result).
 * Only file:// URIs are files on the phone; web blob:/data: URLs have nothing on disk.
 */
export function removeTempFile(uri: string): boolean {
  if (!uri.startsWith('file://')) return false;
  try {
    const f = new File(uri);
    if (f.exists) f.delete();
    return true;
  } catch {
    return false;
  }
}

export type SkyPhotoDeps = {
  reencode: (photo: Photo) => Promise<string>;
  upload: (uri: string) => Promise<SkyImageResponse>;
  remove: (uri: string) => unknown;
};

const DEFAULT_DEPS: SkyPhotoDeps = {
  reencode: reencodePhoto,
  upload: (uri) => uploadSkyImage(uri),
  remove: removeTempFile,
};

/** Re-encode and upload the photo; the original and the re-encoded file are always deleted. */
export async function analyzeSkyPhoto(
  photo: Photo,
  deps: SkyPhotoDeps = DEFAULT_DEPS,
): Promise<SkyImageResponse> {
  const temps = [photo.uri];
  try {
    const clean = await deps.reencode(photo);
    if (clean !== photo.uri) temps.push(clean);
    return await deps.upload(clean);
  } finally {
    for (const uri of temps) deps.remove(uri);
  }
}
