"""Tests for src.sky_cloud and the SWIMSEG split (tiny models, synthetic images; no test split)."""

import json

import numpy as np
import pandas as pd
import pytest
import tensorflow as tf
from PIL import Image
from src import sky_cloud as scl
from src import sky_data as sd

SIZE = 32


def tiny_day14_model():
    """Stand-in for sky_cnn_v1_seed43.keras: conv features -> Dropout -> two softmax heads."""
    inp = tf.keras.Input((SIZE, SIZE, 3), name="image_0_1")
    x = tf.keras.layers.Conv2D(4, 3, activation="relu")(inp)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    out = {
        "ccsn": tf.keras.layers.Dense(11, "softmax", name="ccsn")(x),
        "swim": tf.keras.layers.Dense(6, "softmax", name="swim")(x),
    }
    return tf.keras.Model(inp, out)


def tiny_data(n=8, seed=0):
    rng = np.random.default_rng(seed)
    return {
        "x": rng.integers(0, 256, (n, SIZE, SIZE, 3), dtype=np.uint8),
        "y": rng.uniform(0, 1, n).astype(np.float32),
    }


def test_judge_cloud_boundaries_and_ships():
    ok = scl.judge_cloud({"cnn_mae": 0.10, "rb_mae": 0.13})
    assert ok["passed"].tolist() == [True, True] and scl.ships(ok)
    c1 = scl.judge_cloud({"cnn_mae": 0.101, "rb_mae": 0.20})
    assert c1["passed"].tolist() == [False, True] and not scl.ships(c1)
    c2 = scl.judge_cloud({"cnn_mae": 0.08, "rb_mae": 0.109})
    assert c2["passed"].tolist() == [True, False] and not scl.ships(c2)
    assert c2.loc[1, "value"] == pytest.approx(0.029)


def test_cloud_scores():
    s = scl.cloud_scores(np.array([0.1, 0.5, 0.9]), np.array([0.0, 0.5, 1.0]))
    assert s["n"] == 3
    assert s["mae"] == pytest.approx(0.2 / 3)
    assert s["bias"] == pytest.approx(0.0)
    assert s["rmse"] == pytest.approx(np.sqrt(0.02 / 3))
    assert sum(s["n_by_bin"].values()) == 3


def test_photometric_augmenter_keeps_geometry():
    aug = scl.photometric_augmenter(42)
    kinds = {type(layer).__name__ for layer in aug.layers}
    assert "RandomRotation" not in kinds and "RandomPerspective" not in kinds
    assert "RandomFlip" in kinds and "RandomBrightness" in kinds
    x = np.random.default_rng(0).uniform(0, 1, (2, SIZE, SIZE, 3)).astype(np.float32)
    y = np.asarray(aug(x, training=True))
    assert y.shape == x.shape and y.min() >= 0 and y.max() <= 1


def test_backbone_frozen_only_head_trains_output_in_0_1():
    base = tiny_day14_model()
    ext = scl.feature_extractor(base)
    assert not ext.trainable and ext.output_shape == (None, 4)
    model = scl.build_cloud_model(ext, seed=42)
    assert [w.name for w in model.trainable_weights] == ["kernel", "bias"]  # Dense(1) only
    before = [w.copy() for w in base.get_weights()]
    d = tiny_data()
    model.compile("adam", "mae")
    model.fit(d["x"] / 255.0, d["y"], epochs=1, verbose=0)
    assert all(np.array_equal(a, b) for a, b in zip(before, base.get_weights()))
    p = scl.predict_cloud(model, d["x"])
    assert p.shape == (8,) and p.min() >= 0 and p.max() <= 1


def test_resume_skips_trained_seed_and_logs_each_epoch(tmp_path):
    ext = scl.feature_extractor(tiny_day14_model())
    tr, va = tiny_data(8, 0), tiny_data(4, 1)
    cfg = {"lr": 1e-3, "epochs": 2, "loss": "mae"}
    _, h1 = scl.resume_or_train_cloud(
        ext, tr, va, 42, model_dir=tmp_path, log_dir=tmp_path, cfg=cfg, verbose=0
    )
    assert not h1.get("resumed") and scl.cloud_seed_path(42, tmp_path).exists()
    log = scl.cloud_log_path(42, tmp_path).read_text(encoding="utf-8")
    assert "seed 42 head epoch 1/2" in log
    _, h2 = scl.resume_or_train_cloud(ext, tr, va, 42, model_dir=tmp_path, log_dir=tmp_path)
    assert h2["resumed"] is True
    assert "reloaded from sky_cloud_v1_seed42.keras (not retrained)" in scl.cloud_log_path(
        42, tmp_path
    ).read_text(encoding="utf-8")


@pytest.mark.slow
def test_tflite_export_matches_keras(tmp_path):
    model = scl.build_cloud_model(scl.feature_extractor(tiny_day14_model()), seed=42)
    d = tiny_data(4)
    path = scl.export_tflite(model, tmp_path / "cloud.tflite")
    diff = np.abs(scl.tflite_predict(path, d["x"]) - scl.predict_cloud(model, d["x"]))
    assert diff.max() < 0.02  # float16 weights


def test_run_test_is_guarded(tmp_path, monkeypatch):
    done = tmp_path / "sky_cloud_test.json"
    done.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        scl.run_test(model_dir=tmp_path, test_path=done)

    def no_test_read(*a, **k):
        raise AssertionError("test split must not be read before all seeds exist")

    monkeypatch.setattr(scl, "load_swimseg", no_test_read)
    with pytest.raises(FileNotFoundError):
        scl.run_test(model_dir=tmp_path, test_path=tmp_path / "new.json")


def test_swimseg_test_split_needs_confirmation():
    with pytest.raises(PermissionError):
        sd.load_split("swimseg", "test")


def test_swimseg_split_groups_whole_days_and_meets_rule():
    t = pd.read_csv(sd.SPLIT_DIR / "swimseg_split.csv", dtype={"date": str, "id": str})
    assert len(t) == 1013 and t["id"].is_unique
    assert (t.groupby("date")["split"].nunique() == 1).all()  # a capture day never crosses
    assert (t.groupby("group")["split"].nunique() == 1).all()
    assert (t.groupby("dup_group")["split"].nunique() == 1).all()
    assert sd.split_ok(t)
    assert t["cloud_fraction"].between(0, 1).all()


def test_union_groups_is_transitive():
    g = sd.union_groups(np.array(["d1", "d1", "d2", "d3"]), np.array([0, 1, 1, 3]))
    assert g[0] == g[1] == g[2] and g[3] != g[0]


def test_split_ok_rule():
    t = pd.DataFrame(
        {
            "split": ["train"] * 14 + ["val"] * 3 + ["test"] * 3,
            "cloud_fraction": [0.1, 0.9] * 7 + [0.1, 0.9, 0.5] * 2,
        }
    )
    assert sd.split_ok(t)
    assert not sd.split_ok(t.assign(cloud_fraction=0.5))  # no clear / no overcast mask
    assert not sd.split_ok(t.assign(split=["train"] * 18 + ["val", "test"]))  # shares off


def test_index_swimseg_folders_pairs_and_reads_metadata(tmp_path):
    for folder, ids in (("train", ["0001", "0002"]), ("val", ["0003"]), ("test", [])):
        (tmp_path / folder).mkdir()
        (tmp_path / f"{folder}_labels").mkdir()
        for i in ids:
            Image.new("RGB", (8, 8), (90, 140, 220)).save(tmp_path / folder / f"{i}.png")
            mask = np.zeros((8, 8), np.uint8)
            mask[:2] = 255  # 25 % white = cloud
            Image.fromarray(mask).save(tmp_path / f"{folder}_labels" / f"{i}.png")
    (tmp_path / "metadata.csv").write_text(
        "Number,Date,Time\n0001,20131023,111406\n0002,20131023,111406\n0003,20140620,163745\n",
        encoding="utf-8",
    )
    t = sd.index_swimseg_folders(tmp_path)
    assert t["id"].tolist() == ["0001", "0002", "0003"]
    assert t["capture"].tolist()[0] == "20131023_111406" and t["date"].nunique() == 2
    assert t["cloud_fraction"].tolist() == [0.25, 0.25, 0.25]
    (tmp_path / "metadata.csv").write_text("Number,Date,Time\n0001,1,1\n", encoding="utf-8")
    with pytest.raises(KeyError):
        sd.index_swimseg_folders(tmp_path)


def test_metrics_payload_is_json(tmp_path):
    """Payload values written by run_train/run_test are plain JSON (numpy floats handled)."""
    s = scl.cloud_scores(np.array([0.2]), np.array([0.25]))
    assert json.loads(json.dumps(s, default=float))["n"] == 1
