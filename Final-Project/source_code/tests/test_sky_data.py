"""Tests for src.sky_data (synthetic images in tmp_path; no downloads)."""

import zipfile

import numpy as np
import pandas as pd
import pytest
from PIL import Image

from src import sky_data as sd


def save_img(path, arr):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(path)
    return path


def textured(seed, size=64):
    rng = np.random.default_rng(seed)
    base = rng.uniform(0, 255, (8, 8, 3))
    return np.kron(base, np.ones((size // 8, size // 8, 1)))


@pytest.fixture
def class_tree(tmp_path):
    """3 classes x 20 distinct images, plus one exact copy and one rotated copy."""
    root = tmp_path / "ds"
    for c, name in enumerate(["A-Clear Sky", "B-Patterned Clouds", "C-Veil Clouds"]):
        for k in range(20):
            save_img(root / name / f"{k}.png", textured(100 * c + k))
    save_img(root / "A-Clear Sky" / "copy.png", textured(0))
    save_img(root / "A-Clear Sky" / "rot.png", np.rot90(textured(1), 1))
    save_img(root / "__MACOSX" / "A-Clear Sky" / "._0.png", textured(5))
    return root


def test_verify_checksums(tmp_path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"uv guard")
    assert sd.verify(p, {"md5": sd.file_hash(p, "md5")})
    assert sd.verify(p, {"sha256": sd.file_hash(p, "sha256")})
    assert not sd.verify(p, {"md5": "0" * 32})


def test_extract_zip_once(tmp_path):
    arc = tmp_path / "x.zip"
    with zipfile.ZipFile(arc, "w") as z:
        z.writestr("folder/a.txt", "hi")
    out = sd.extract(arc, tmp_path / "out")
    assert (out / "folder" / "a.txt").read_text() == "hi"
    (out / "folder" / "a.txt").write_text("changed")
    sd.extract(arc, out)  # already extracted -> untouched
    assert (out / "folder" / "a.txt").read_text() == "changed"


def test_index_skips_macos_files_and_maps_labels(class_tree):
    df = sd.index_classification(class_tree, "swimcat_ext", sd.swimcat_ext_label)
    assert len(df) == 62
    assert set(df["label"]) == {"clear_sky", "patterned_clouds", "veil_clouds"}
    assert not df["path"].str.contains("MACOSX").any()
    with pytest.raises(FileNotFoundError):
        sd.index_classification(class_tree / "missing", "x")


def test_duplicates_found_even_when_rotated(class_tree):
    df = sd.index_classification(class_tree, "t")
    thumbs = np.stack([sd.thumbnail(sd.resolve(p)) for p in df["path"]])
    key = df["path"].str.split("/").str[-2:].str.join("/")  # "<class>/<file>" is unique
    groups = pd.Series(sd.duplicate_groups(thumbs), index=key)
    assert groups["A-Clear Sky/copy.png"] == groups["A-Clear Sky/0.png"]
    assert groups["A-Clear Sky/rot.png"] == groups["A-Clear Sky/1.png"]
    assert groups.value_counts().max() == 2  # distinct images are not chained together


def test_splits_stratified_grouped_and_reproducible(class_tree):
    df = sd.index_classification(class_tree, "t")
    t1 = sd.build_split_table(df, df["label"])
    t2 = sd.build_split_table(df, df["label"])
    assert (t1["split"] == t2["split"]).all()
    assert t1.groupby("dup_group")["split"].nunique().max() == 1
    counts = pd.crosstab(t1["label"], t1["split"])
    assert (counts[["train", "val", "test"]] > 0).all().all()
    share = t1["split"].value_counts(normalize=True)
    assert share["train"] == pytest.approx(0.7, abs=0.08)
    assert not t1["label_conflict"].any()


def test_label_conflict_flag(tmp_path):
    root = tmp_path / "ds"
    save_img(root / "Ns" / "a.png", textured(7))
    save_img(root / "St" / "a.png", textured(7))  # same photo, other genus
    save_img(root / "St" / "b.png", textured(8))
    t = sd.build_split_table(sd.index_classification(root, "c"), pd.Series(["Ns", "St", "St"]))
    assert t["label_conflict"].tolist() == [True, True, False]


def test_load_split_guards_test(tmp_path):
    pd.DataFrame({"path": ["a", "b"], "split": ["train", "test"]}).to_csv(
        tmp_path / "x_split.csv", index=False
    )
    assert len(sd.load_split("x", "train", tmp_path)) == 1
    with pytest.raises(PermissionError):
        sd.load_split("x", "test", tmp_path)
    assert len(sd.load_split("x", "test", tmp_path, confirm_test=True)) == 1


def test_swimseg_pairs_and_cloud_fraction(tmp_path):
    root = tmp_path / "swimseg"
    save_img(root / "images" / "0001.png", textured(1))
    mask = np.zeros((10, 10, 3))
    mask[:3] = 255  # 30 % cloud
    save_img(root / "GTmaps" / "0001_GT.png", mask)
    save_img(root / "images" / "0002.png", textured(2))  # no mask -> skipped
    df = sd.index_swimseg(root)
    assert len(df) == 1 and df.loc[0, "cloud_fraction"] == pytest.approx(0.3)


def test_load_image_crops_square_and_scales(tmp_path):
    arr = np.zeros((40, 80, 3))
    arr[:, 20:60] = 255  # white centre square
    img = sd.load_image(save_img(tmp_path / "w.png", arr), size=32)
    assert img.shape == (32, 32, 3) and img.dtype == np.float32
    assert img.min() >= 0 and img.max() <= 1 and img.mean() > 0.95


def test_augmenter_shape_range_and_identity_at_inference():
    aug = sd.augmenter(seed=1)
    x = np.random.default_rng(0).uniform(0, 1, (4, 32, 32, 3)).astype("float32")
    y = np.asarray(aug(x, training=True))
    assert y.shape == x.shape and y.min() >= 0 and y.max() <= 1.0 + 1e-6
    assert not np.allclose(y, x)
    np.testing.assert_allclose(np.asarray(aug(x, training=False)), x, atol=1e-6)
