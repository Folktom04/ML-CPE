"""Tests for src.quantile (synthetic data with a known noise distribution)."""

import numpy as np
import pandas as pd
import pytest

from src import quantile as qr
from tests.test_train_multi import FEATURES, synthetic

SMALL = {
    "objective": "reg:quantileerror",
    "quantile_alpha": np.array(qr.QUANTILES),
    "n_estimators": 150,
    "learning_rate": 0.1,
    "max_depth": 3,
    "random_state": 42,
}
Z90 = 1.2815515655446004  # standard normal 0.9 quantile


def test_quantile_params_use_tuned_params_and_quantile_objective():
    p = qr.quantile_params()
    assert p["objective"] == "reg:quantileerror"
    assert list(p["quantile_alpha"]) == qr.QUANTILES
    assert "learning_rate" in p and "n_estimators" in p


def test_pinball_loss_known_values():
    # y above q: alpha * d; y below q: (1 - alpha) * |d|
    assert qr.pinball_loss([2.0], [1.0], 0.9) == pytest.approx(0.9)
    assert qr.pinball_loss([0.0], [1.0], 0.9) == pytest.approx(0.1)
    assert qr.pinball_loss([1.0, 1.0], [1.0, 1.0], 0.5) == 0.0


def test_interval_metrics_counts():
    m = qr.interval_metrics([0, 1, 2, 3], [0.5] * 4, [2.5] * 4)
    assert m == {"n": 4, "coverage": 0.5, "below": 0.25, "above": 0.25, "width": 2.0}


def test_quantile_model_covers_known_gaussian_and_never_crosses():
    df = synthetic(n_per_year=1200, noise=0.05)
    train, dev = df[df["time_utc"].dt.year == 2023], df[df["time_utc"].dt.year == 2024]
    model = qr.fit_quantile(train[FEATURES], train["cmf_uvi"], None, SMALL)
    q = qr.predict_quantiles(model, dev[FEATURES])
    assert list(q.columns) == qr.QCOLS
    assert (np.diff(q.to_numpy(), axis=1) >= 0).all()
    assert q.to_numpy().min() >= 0 and q.to_numpy().max() <= 1
    m = qr.interval_metrics(dev["cmf_uvi"], q["q10"], q["q90"])
    assert 0.7 <= m["coverage"] <= 0.9
    assert m["width"] == pytest.approx(2 * Z90 * 0.05, rel=0.3)
    # UVI scale keeps the coverage (uvi_clear > 0)
    uvi = qr.to_uvi(dev, q)
    assert qr.interval_metrics(dev["nasa_uvi"], uvi["q10"], uvi["q90"])[
        "coverage"
    ] == pytest.approx(m["coverage"])


def test_cqr_fixes_a_too_narrow_interval():
    rng = np.random.default_rng(0)
    y_cal, y_new = 0.5 + rng.normal(0, 0.1, 4000), 0.5 + rng.normal(0, 0.1, 4000)
    lo, hi = np.full(4000, 0.45), np.full(4000, 0.55)
    q = qr.cqr_correction(y_cal, lo, hi)
    assert q == pytest.approx(Z90 * 0.1 - 0.05, abs=0.01)
    cmf_q = pd.DataFrame({"q10": lo, "q50": 0.5, "q75": 0.52, "q90": hi})
    adj = qr.apply_cqr(cmf_q, q)
    assert qr.interval_metrics(y_new, adj["q10"], adj["q90"])["coverage"] == pytest.approx(
        0.8, abs=0.03
    )
    # a too-wide interval gets a negative correction
    assert qr.cqr_correction(y_cal, lo - 0.3, hi + 0.3) < 0


def test_apply_cqr_keeps_order_and_range():
    cmf_q = pd.DataFrame(
        {"q10": [0.1, 0.5], "q50": [0.2, 0.6], "q75": [0.3, 0.7], "q90": [0.4, 0.95]}
    )
    wide = qr.apply_cqr(cmf_q, 0.2)
    assert wide["q10"].tolist() == pytest.approx([0.0, 0.3])
    assert wide["q90"].tolist() == pytest.approx([0.6, 1.0])
    narrow = qr.apply_cqr(cmf_q, -0.5)  # would cross q50 -> capped at q50
    assert (narrow["q10"] <= narrow["q50"]).all() and (narrow["q90"] >= narrow["q50"]).all()
    assert (narrow["q75"] <= narrow["q90"]).all()


def test_alert_report_counts():
    true = np.array([12.0, 11.2, 9.0, 5.0, 8.0, 3.0])
    pred = np.array([11.0, 9.0, 11.5, 8.2, 7.0, 3.0])
    r = qr.alert_report(true, pred)
    ext, vh = r["Extreme"], r["Very high"]
    assert (ext["tp"], ext["fp"], ext["fn"]) == (1, 1, 1)
    assert ext["recall"] == 0.5 and ext["precision"] == 0.5
    assert ext["false_alarm_rate"] == pytest.approx(1 / 4)
    # >= Very high: events 12, 11.2, 9, 8 ; alerts 11, 9, 11.5, 8.2
    assert (vh["tp"], vh["fp"], vh["fn"]) == (3, 1, 1)
    assert vh["false_alarm_rate"] == pytest.approx(1 / 2)


def _alert_rows(values):
    rows = []
    for qc, (rec_ext, prec_vh) in values.items():
        rows.append({"quantile": qc, "level": "Extreme", "recall": rec_ext, "precision": 0.9})
        rows.append({"quantile": qc, "level": "Very high", "recall": 0.9, "precision": prec_vh})
    return pd.DataFrame(rows)


def test_select_alert_quantile_lowest_passing_or_q90():
    table = _alert_rows({"q50": (0.3, 0.9), "q75": (0.85, 0.6), "q90": (0.95, 0.4)})
    assert qr.select_alert_quantile(table)[:2] == ("q75", True)
    none = _alert_rows({"q50": (0.3, 0.9), "q75": (0.7, 0.6), "q90": (0.95, 0.4)})
    q, ok, reason = qr.select_alert_quantile(none)
    assert (q, ok) == ("q90", False) and "none passes" in reason


def test_score_part_and_coverage_by():
    df = synthetic(n_per_year=600, noise=0.05)
    model = qr.fit_quantile(df[FEATURES], df["cmf_uvi"], None, SMALL)
    q = qr.predict_quantiles(model, df[FEATURES])
    res = qr.score_part(df, q)
    assert set(res["pinball"]) == set(qr.QCOLS)
    assert len(res["alerts"]) == len(qr.ALERT_CANDIDATES) * 2
    uvi = qr.to_uvi(df, q)
    table = qr.coverage_by(df, q, qr.uvi_bins(uvi["q50"]))
    assert table["n"].sum() == len(df)
    assert set(table["group"]) <= set(qr.WHO_LEVELS_EN)


def test_oof_quantiles_refuse_test_year():
    df = synthetic()
    late = df.assign(time_utc=df["time_utc"] + pd.Timedelta(days=366))
    with pytest.raises(AssertionError):
        qr.oof_quantiles(late, FEATURES, folds=(5,), params=SMALL)
