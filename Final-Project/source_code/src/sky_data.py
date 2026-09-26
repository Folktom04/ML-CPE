"""Day 13: public sky-image datasets for the separate sky-CNN module.

Datasets (licences checked on day 13, details in ``docs/datasets.md``):

* CCSN (Harvard Dataverse doi:10.7910/DVN/CADDPD, CC0 1.0): 2,543 normal-camera cloud photos,
  11 cloud genera.
* SWIMCAT-ext (Mendeley Data doi:10.17632/vwdd9grvdp.1, CC BY 4.0): 2,100 sky-camera patches,
  6 classes; used instead of SWIMCAT while the SWIMCAT/SWIMSEG request forms are pending.
* SWIMSEG (CC BY-NC 4.0, request form): sky patches + binary cloud masks; indexed only when the
  archive has been placed in ``dataset/sky/raw/`` by hand.

Each dataset keeps its own labels and its own train/val/test split (no merged taxonomy).
Near-duplicate images are kept in the same split: two images are near-duplicates when the mean
absolute difference of their 16x16 RGB thumbnails, minimised over the 8 rotations/flips, is below
``DUP_MAX_MAD`` (0.03, chosen on day 13 by viewing pairs; dHash alone chained unrelated
low-texture images and missed rotated copies). Test splits are only readable with an
explicit confirmation flag (day 14, after the criteria are declared).
Run from the project root: ``PYTHONPATH=source_code python -m src.sky_data --download --index``.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from PIL import Image

from src.fetch_data import ROOT

SKY_DIR = ROOT / "dataset" / "sky"
RAW_DIR = SKY_DIR / "raw"
SPLIT_DIR = ROOT / "docs" / "sky_splits"
IMAGE_SIZE = 224
SPLIT_FRACTIONS = (0.70, 0.15, 0.15)
SEED = 42
THUMB_SIZE = 16
DUP_MAX_MAD = 0.03
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

SOURCES: dict[str, dict[str, Any]] = {
    "ccsn": {
        "url": "https://dataverse.harvard.edu/api/access/datafile/3569338",
        "file": "CCSN.zip",
        "md5": "0787f50947a3f65630a7463206316fd3",
        "license": "CC0 1.0",
        "doi": "10.7910/DVN/CADDPD",
    },
    "swimcat_ext": {
        "url": (
            "https://data.mendeley.com/public-files/datasets/vwdd9grvdp/files/"
            "82823b0b-273f-40fe-89ab-cdac6e069149/file_downloaded"
        ),
        "file": "Swimcat-ext.rar",
        "sha256": "c4f8883cd9fc0a163b2853ec5d75d1d06ea76f350a6905dee90359dfc99fe2d4",
        "license": "CC BY 4.0",
        "doi": "10.17632/vwdd9grvdp.1",
    },
}


def file_hash(path: Path, algo: str) -> str:
    """Hex digest of a file.

    Args:
        path: File.
        algo: ``"md5"`` or ``"sha256"``.

    Returns:
        Hex digest.
    """
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path: Path, source: dict[str, Any]) -> bool:
    """Check a downloaded archive against the published checksum.

    Args:
        path: Archive.
        source: Entry of ``SOURCES``.

    Returns:
        True when the md5/sha256 matches.
    """
    for algo in ("sha256", "md5"):
        if algo in source:
            return file_hash(path, algo) == source[algo]
    return False


def download(name: str, raw_dir: Path = RAW_DIR, retries: int = 4) -> Path:
    """Download one archive with retries/backoff; skip when a verified copy exists.

    Args:
        name: Key of ``SOURCES``.
        raw_dir: Target directory.
        retries: Attempts before giving up.

    Returns:
        Path of the verified archive.
    """
    src = SOURCES[name]
    path = raw_dir / src["file"]
    if path.exists() and verify(path, src):
        return path
    raw_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    for attempt in range(retries):
        try:
            with requests.get(src["url"], stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            tmp.replace(path)
            if verify(path, src):
                return path
            raise OSError(f"checksum mismatch for {path.name}")
        except (requests.RequestException, OSError):
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    return path


def extract(archive: Path, out_dir: Path) -> Path:
    """Extract a .zip (zipfile) or .rar (Windows/bsdtar ``tar``) once.

    Args:
        archive: Archive file.
        out_dir: Destination directory (skipped when it already has files).

    Returns:
        ``out_dir``.
    """
    if out_dir.exists() and any(out_dir.rglob("*")):
        return out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(out_dir)
    else:
        subprocess.run(["tar", "-xf", str(archive), "-C", str(out_dir)], check=True)
    return out_dir


def _images(folder: Path) -> list[Path]:
    """Image files under ``folder`` (recursive), skipping macOS metadata (``__MACOSX``, ``._*``).

    Args:
        folder: Directory to scan.

    Returns:
        Sorted list of image paths.
    """
    return sorted(
        p
        for p in folder.rglob("*")
        if p.suffix.lower() in IMAGE_EXT
        and "__MACOSX" not in p.parts
        and not p.name.startswith("._")
    )


def _rel(p: Path) -> str:
    """Path relative to ``SKY_DIR`` when inside it, else absolute (POSIX separators)."""
    try:
        return p.relative_to(SKY_DIR).as_posix()
    except ValueError:
        return p.as_posix()


def index_classification(
    root: Path, dataset: str, label_from_dir: Callable[[str], str] | None = None
) -> pd.DataFrame:
    """Index a folder-per-class dataset.

    Args:
        root: Directory whose image files sit in one folder per class.
        dataset: Dataset name stored in the table.
        label_from_dir: Optional function mapping a folder name to the label.

    Returns:
        Table with ``dataset``, ``path`` (relative to ``SKY_DIR`` when possible) and ``label``.
    """
    rows = []
    for p in _images(root):
        folder = p.parent.name
        label = label_from_dir(folder) if label_from_dir else folder
        rows.append({"dataset": dataset, "path": _rel(p), "label": label})
    if not rows:
        raise FileNotFoundError(f"no images under {root}")
    return pd.DataFrame(rows)


def swimcat_ext_label(folder: str) -> str:
    """``"B-Patterned Clouds"`` -> ``"patterned_clouds"``.

    Args:
        folder: Class folder name of SWIMCAT-ext.

    Returns:
        Snake-case label without the letter prefix.
    """
    name = folder.split("-", 1)[1] if "-" in folder else folder
    return name.strip().lower().replace(" ", "_")


def cloud_fraction(mask_path: Path) -> float:
    """Share of cloud pixels in a binary mask (values > 127 count as cloud).

    Args:
        mask_path: Mask image.

    Returns:
        Fraction in [0, 1].
    """
    m = np.asarray(Image.open(mask_path).convert("L"))
    return float((m > 127).mean())


def index_swimseg(root: Path) -> pd.DataFrame:
    """Pair SWIMSEG images with masks by file stem (mask stems end with ``_GT``).

    Args:
        root: Extracted SWIMSEG directory.

    Returns:
        Table with ``dataset``, ``path``, ``mask_path`` and ``cloud_fraction``.
    """
    files = _images(root)
    masks = {p.stem[:-3]: p for p in files if p.stem.upper().endswith("_GT")}
    rows = []
    for p in files:
        if p.stem.upper().endswith("_GT") or p.stem not in masks:
            continue
        mp = masks[p.stem]
        rows.append(
            {
                "dataset": "swimseg",
                "path": _rel(p),
                "mask_path": _rel(mp),
                "cloud_fraction": cloud_fraction(mp),
            }
        )
    if not rows:
        raise FileNotFoundError(f"no image/mask pairs under {root}")
    return pd.DataFrame(rows)


def resolve(path: str) -> Path:
    """Absolute path of an index entry (relative entries are under ``SKY_DIR``).

    Args:
        path: Path from an index/split table.

    Returns:
        Absolute path.
    """
    p = Path(path)
    return p if p.is_absolute() else SKY_DIR / p


def thumbnail(path: Path, size: int = THUMB_SIZE) -> np.ndarray:
    """Small RGB thumbnail in [0, 1] used for near-duplicate detection.

    Args:
        path: Image file.
        size: Thumbnail side.

    Returns:
        (size, size, 3) float32 array.
    """
    img = Image.open(path).convert("RGB").resize((size, size), Image.BILINEAR)
    return np.asarray(img, dtype=np.float32) / 255.0


def dihedral(thumbs: np.ndarray) -> np.ndarray:
    """The 8 rotations/flips of a stack of square thumbnails.

    Args:
        thumbs: (n, s, s, 3) array.

    Returns:
        (8, n, s, s, 3) array.
    """
    out = []
    for k in range(4):
        r = np.rot90(thumbs, k, axes=(1, 2))
        out += [r, r[:, :, ::-1]]
    return np.stack(out)


def duplicate_groups(thumbs: np.ndarray, max_mad: float = DUP_MAX_MAD) -> np.ndarray:
    """Group ids so that near-duplicate images (transitively) share a group.

    A pair is a near-duplicate when the mean absolute difference of the thumbnails, minimised
    over the 8 rotations/flips of the second image, is below ``max_mad``.

    Args:
        thumbs: (n, s, s, 3) thumbnails.
        max_mad: Largest distance treated as a near-duplicate.

    Returns:
        Group id per image.
    """
    n = len(thumbs)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    flat = thumbs.reshape(n, -1)
    d8 = dihedral(thumbs).reshape(8, n, -1)
    for i in range(n - 1):
        dist = np.abs(d8[:, i + 1 :, :] - flat[i]).mean(axis=2).min(axis=0)
        for j in np.nonzero(dist < max_mad)[0] + i + 1:
            ri, rj = find(i), find(int(j))
            if ri != rj:
                parent[rj] = ri
    return np.array([find(i) for i in range(n)])


def make_splits(
    df: pd.DataFrame,
    strata: pd.Series,
    groups: np.ndarray,
    fractions: tuple[float, float, float] = SPLIT_FRACTIONS,
    seed: int = SEED,
) -> pd.Series:
    """Stratified train/val/test assignment where every duplicate group stays together.

    Groups are shuffled within each stratum (stratum of a group = its first member) and filled
    into train, val and test in order until each reaches its share.

    Args:
        df: Index table.
        strata: Stratum per row (class label or cloud-fraction bin).
        groups: Duplicate-group id per row.
        fractions: Train/val/test shares.
        seed: Random seed.

    Returns:
        Split name per row (``"train"``, ``"val"``, ``"test"``).
    """
    rng = np.random.default_rng(seed)
    g = pd.Series(groups, index=df.index)
    first_stratum = strata.groupby(g).first()
    sizes = g.value_counts()
    group_split: dict[Any, str] = {}
    for stratum in sorted(first_stratum.unique(), key=str):
        gids = first_stratum.index[first_stratum == stratum].to_numpy().copy()  # writable
        rng.shuffle(gids)
        bounds = np.cumsum(fractions)[:2] * int(sizes[gids].sum())
        filled = 0
        for gid in gids:
            group_split[gid] = (
                "train" if filled < bounds[0] else ("val" if filled < bounds[1] else "test")
            )
            filled += int(sizes[gid])
    return g.map(group_split)


def build_split_table(df: pd.DataFrame, strata: pd.Series, seed: int = SEED) -> pd.DataFrame:
    """Group near-duplicates and split one dataset's index table.

    Args:
        df: Index table (``path`` column).
        strata: Stratum per row.
        seed: Random seed.

    Returns:
        Copy with ``dup_group``, ``split`` and (when there is a ``label`` column)
        ``label_conflict`` = the image's near-duplicate group carries more than one label.
    """
    out = df.copy()
    thumbs = np.stack([thumbnail(resolve(p)) for p in out["path"]])
    out["dup_group"] = duplicate_groups(thumbs)
    out["split"] = make_splits(out, strata, out["dup_group"].to_numpy(), seed=seed)
    if "label" in out:
        out["label_conflict"] = out.groupby("dup_group")["label"].transform("nunique") > 1
    return out


def load_split(
    dataset: str, split: str, split_dir: Path = SPLIT_DIR, confirm_test: bool = False
) -> pd.DataFrame:
    """Rows of one split; the test split needs ``confirm_test=True`` (day 14, after criteria).

    Args:
        dataset: ``"ccsn"``, ``"swimcat_ext"`` or ``"swimseg"``.
        split: ``"train"``, ``"val"`` or ``"test"``.
        split_dir: Directory with ``<dataset>_split.csv``.
        confirm_test: Must be True to read the test split.

    Returns:
        Filtered table.
    """
    if split == "test" and not confirm_test:
        raise PermissionError("sky test splits are read once on day 14 (confirm_test=True)")
    df = pd.read_csv(split_dir / f"{dataset}_split.csv")
    return df.loc[df["split"] == split].reset_index(drop=True)


def load_image(path: Path, size: int = IMAGE_SIZE) -> np.ndarray:
    """Centre-crop to a square, resize and scale to float32 [0, 1] RGB.

    Args:
        path: Image file.
        size: Output side length.

    Returns:
        (size, size, 3) array.
    """
    img = Image.open(path).convert("RGB")
    w, h = img.size
    s = min(w, h)
    left, top = (w - s) // 2, (h - s) // 2
    img = img.crop((left, top, left + s, top + s)).resize((size, size), Image.BILINEAR)
    return np.asarray(img, dtype=np.float32) / 255.0


def augmenter(seed: int = SEED) -> Any:
    """Keras augmentation pipeline for [0, 1] RGB images (training only).

    Photometric: brightness, contrast, white balance (random per-channel gain), saturation,
    blur. Geometric: horizontal flip, rotation ±15°, mild perspective (phone tilt). All layers
    are identity at inference (``training=False``).

    Args:
        seed: Seed for every random layer.

    Returns:
        ``keras.Sequential`` taking and returning (N, H, W, 3) in [0, 1].
    """
    import keras

    class RandomWhiteBalance(keras.layers.Layer):
        """Multiply each RGB channel by a random gain in [1 - delta, 1 + delta]."""

        def __init__(self, delta: float = 0.12, seed: int | None = None, **kw: Any) -> None:
            super().__init__(**kw)
            self.delta = delta
            self.gen = keras.random.SeedGenerator(seed)

        def call(self, x: Any, training: bool | None = None) -> Any:
            if not training:
                return x
            n = keras.ops.shape(x)[0]
            gain = keras.random.uniform((n, 1, 1, 3), 1 - self.delta, 1 + self.delta, seed=self.gen)
            return keras.ops.clip(x * gain, 0.0, 1.0)

    rng = (0.0, 1.0)
    return keras.Sequential(
        [
            keras.layers.RandomFlip("horizontal", seed=seed),
            keras.layers.RandomRotation(15 / 360, fill_mode="reflect", seed=seed),
            keras.layers.RandomPerspective(factor=0.15, scale=0.8, seed=seed),
            keras.layers.RandomBrightness(0.2, value_range=rng, seed=seed),
            keras.layers.RandomContrast(0.2, value_range=rng, seed=seed),
            RandomWhiteBalance(0.12, seed=seed),
            keras.layers.RandomSaturation((0.4, 0.6), value_range=rng, seed=seed),
            keras.layers.RandomGaussianBlur(
                factor=0.5, sigma=(0.1, 1.2), value_range=rng, seed=seed
            ),
        ],
        name="sky_augment",
    )


def split_summary(table: pd.DataFrame, label_col: str = "label") -> pd.DataFrame:
    """Counts per label and split, with totals.

    Args:
        table: Split table.
        label_col: Column tabulated against ``split``.

    Returns:
        Crosstab.
    """
    ct = pd.crosstab(table[label_col], table["split"], margins=True)
    return ct[[c for c in ("train", "val", "test", "All") if c in ct.columns]]


def main(argv: list[str] | None = None) -> None:
    """Download (CCSN, SWIMCAT-ext), extract, index, hash and split every available dataset.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    parser = argparse.ArgumentParser(description="Day 13: sky-image datasets")
    parser.add_argument("--download", action="store_true", help="fetch CCSN and SWIMCAT-ext")
    parser.add_argument("--index", action="store_true", help="index + split available datasets")
    args = parser.parse_args(argv)

    if args.download:
        for name in SOURCES:
            path = download(name)
            extract(path, SKY_DIR / name)
            print(f"{name}: {path.name} checksum ok -> {SKY_DIR / name}")

    if args.index:
        SPLIT_DIR.mkdir(parents=True, exist_ok=True)
        tables = {
            "ccsn": index_classification(SKY_DIR / "ccsn", "ccsn"),
            "swimcat_ext": index_classification(
                SKY_DIR / "swimcat_ext", "swimcat_ext", swimcat_ext_label
            ),
        }
        for name, df in tables.items():
            t = build_split_table(df, df["label"])
            t.to_csv(SPLIT_DIR / f"{name}_split.csv", index=False)
            n_dup = int((t.groupby("dup_group")["path"].transform("size") > 1).sum())
            print(
                f"\n{name}: {len(t)} images, {n_dup} in near-duplicate groups, "
                f"{int(t['label_conflict'].sum())} with conflicting labels"
            )
            print(split_summary(t).to_string())
        seg = SKY_DIR / "swimseg"
        if seg.exists():
            df = index_swimseg(seg)
            bins = pd.cut(df["cloud_fraction"], [-0.01, 0.2, 0.4, 0.6, 0.8, 1.0]).astype(str)
            t = build_split_table(df, bins)
            t.to_csv(SPLIT_DIR / "swimseg_split.csv", index=False)
            print(f"\nswimseg: {len(t)} images")
        else:
            print("\nswimseg: not available yet (request form pending)")


if __name__ == "__main__":
    main()
