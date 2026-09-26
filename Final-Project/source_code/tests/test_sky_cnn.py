"""Tests for src.sky_cnn (tiny untrained models, synthetic images; no downloads)."""

import numpy as np
import pandas as pd
import pytest
import tensorflow as tf

from src import sky_cnn as sc

SIZE = 64
TINY = {"lr": 1e-3, "epochs": 1}


def tiny_split(n=6, seed=0):
    """Synthetic uint8 images for both datasets."""
    rng = np.random.default_rng(seed)
    x1 = rng.integers(0, 256, (n, SIZE, SIZE, 3), dtype=np.uint8)
    x2 = rng.integers(0, 256, (n, SIZE, SIZE, 3), dtype=np.uint8)
    return {
        "ccsn": {"x": x1, "y": rng.integers(0, 11, n).astype(np.int32)},
        "swim": {"x": x2, "y": rng.integers(0, 6, n).astype(np.int32), "groups": np.arange(n)},
    }


def test_check_unit_range_rejects_0_255_input():
    sc.check_unit_range(np.zeros((2, 4, 4, 3), np.float32))
    sc.check_unit_range(np.ones((4, 4, 3), np.float32))
    with pytest.raises(ValueError):
        sc.check_unit_range(np.full((4, 4, 3), 200.0, np.float32))  # 0-255 floats
    with pytest.raises(TypeError):
        sc.check_unit_range(np.zeros((4, 4, 3), np.uint8))


def test_model_feeds_0_255_to_mobilenet_preprocessing():
    model, backbone = sc.build_model(SIZE, weights=None)
    to255 = tf.keras.Model(model.input, model.get_layer("to_0_255").output)
    x = np.stack([np.zeros((SIZE, SIZE, 3)), np.ones((SIZE, SIZE, 3))]).astype(np.float32)
    y = np.asarray(to255(x))
    assert y[0].max() == 0.0 and y[1].min() == pytest.approx(255.0)
    # MobileNetV3's own preprocessing (include_preprocessing=True) maps 0-255 to [-1, 1]
    resc = [l for l in backbone.layers if isinstance(l, tf.keras.layers.Rescaling)]
    assert resc, "MobileNetV3 built-in preprocessing layer missing"
    inner = tf.keras.Model(backbone.input, resc[0].output)
    z = np.asarray(inner(y))
    assert z[0].min() == pytest.approx(-1.0) and z[1].max() == pytest.approx(1.0)
    out = model(x)
    assert out["ccsn"].shape == (2, 11) and out["swim"].shape == (2, 6)
    np.testing.assert_allclose(np.asarray(out["ccsn"]).sum(axis=1), 1.0, rtol=1e-5)


def test_dataset_pipeline_outputs_unit_range_and_masks():
    d = sc.combine(*tiny_split().values())
    assert d["w_ccsn"].tolist() == [1.0] * 6 + [0.0] * 6
    assert d["w_swim"].tolist() == [0.0] * 6 + [1.0] * 6
    for training in (False, True):
        x, y, w = next(iter(sc.make_dataset(d, training, seed=1, batch=12)))
        x = np.asarray(x)
        assert x.dtype == np.float32 and x.min() >= 0.0 and x.max() <= 1.0 + 1e-6
        assert set(y) == {"ccsn", "swim"} and set(w) == {"ccsn", "swim"}


def test_group_matrix_and_ccsn_group_scores():
    g = sc.group_matrix()
    assert g.shape == (11, 4) and (g.sum(axis=1) == 1).all()
    ci, cs, cu = (sc.CCSN_CLASSES.index(c) for c in ("Ci", "Cs", "Cu"))
    y = np.array([ci, cu])
    p = np.zeros((2, 11), np.float32)
    p[0, cs] = 0.6  # wrong genus, right UV group
    p[0, cu] = 0.4
    p[1, cu] = 1.0
    s = sc.ccsn_scores(p, y)
    assert s["accuracy"] == 0.5 and s["group_accuracy"] == 1.0
    assert s["group_recall"]["high_thin"] == 1.0 and np.isnan(s["group_recall"]["mid"])


def test_swim_group_accuracy_counts_each_group_once():
    y = np.array([0, 0, 0, 1])
    groups = np.array([7, 7, 7, 9])  # three near-duplicates + one single image
    p = np.array([[0.4, 0.6], [0.9, 0.1], [0.9, 0.1], [0.2, 0.8]])
    p = np.pad(p, ((0, 0), (0, 4)))
    s = sc.swim_scores(p, y, groups)
    assert s["n_images"] == 4 and s["n_groups"] == 2
    assert s["accuracy"] == 0.75 and s["group_accuracy"] == 1.0


def test_red_blue_cloud_fraction():
    blue = np.tile(np.array([0.2, 0.5, 0.9], np.float32), (8, 8, 1))
    grey = np.full((8, 8, 3), 0.6, np.float32)
    assert sc.rb_cloud_fraction(blue) == 0.0
    assert sc.rb_cloud_fraction(grey) == 1.0
    half = np.concatenate([blue[:4], grey[:4]])
    assert sc.rb_cloud_fraction(np.stack([half, blue])).tolist() == [0.5, 0.0]
    with pytest.raises(ValueError):
        sc.rb_cloud_fraction(grey * 255)


def test_judge_thresholds():
    res = {
        "ccsn": {
            "accuracy": 0.62,
            "macro_f1": 0.54,
            "group_accuracy": 0.8,
            "group_recall": {"high_thin": 0.7},
        },
        "ccsn_baseline_acc": 0.5,
        "swim": {"accuracy": 0.9, "group_accuracy": 0.79},
        "swim_baseline_group_acc": 0.7,
        "rb_median": {
            "clear_sky": 0.1,
            "thick_white_clouds": 0.9,
            "thick_dark_clouds": 0.7,
            "veil_clouds": 0.6,
        },
    }
    v = sc.judge(res).set_index("id")["passed"].to_dict()
    assert v["K1"] and not v["K2"] and v["K3"] and v["K4"] and v["K5"]
    assert v["S1"] and not v["S2"] and v["S3"]
    assert v["R1"] and not v["R2"]  # veil 0.60 is not > 0.60


def test_train_export_and_predict_sky_match(tmp_path):
    data = tiny_split()
    model, hist = sc.train_seed(
        data, data, seed=3, weights=None, stage1=TINY, stage2={**TINY, "unfreeze_from": 0.7}
    )
    assert np.isfinite(hist["best_val_loss"])
    path = sc.export_tflite(model, tmp_path / "m.tflite")
    img = data["swim"]["x"][0].astype(np.float32) / 255.0
    res = sc.predict_sky(img, tflite_path=path)
    keras_probs = model.predict(img[None], verbose=0)
    kg = np.asarray(keras_probs["ccsn"])[0] @ sc.group_matrix()
    got = np.array([res["cloud_group_probs"][g] for g in sc.UV_GROUPS])
    np.testing.assert_allclose(got, kg, atol=2e-2)  # float16 export
    assert res["cloud_group_th"] in sc.UV_GROUP_TH.values() and 0 <= res["cloud_fraction_rb"] <= 1
    with pytest.raises(ValueError):
        sc.predict_sky(img * 255, tflite_path=path)


def test_run_test_refuses_second_run(tmp_path, monkeypatch):
    done = tmp_path / "t.json"
    done.write_text("{}")
    monkeypatch.setattr(sc, "TEST_PATH", done)
    with pytest.raises(FileExistsError):
        sc.run_test()
