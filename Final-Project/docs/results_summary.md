# UV Guard — results summary, days 1–14 (for the report)

Every number below is copied from a saved result file; the source is given next to each table as
`[file]`. Rounded to 3 decimals unless the file itself is quoted. "dev" = 2024 (models fit on
2023); "test" = 2025 (models refit on 2023–2024, evaluated once). **No physical UV instrument was
used**: targets and references are satellite/model products (NASA POWER, OMI, TEMIS).

---

## 1. Target source and dataset (days 2–5)

**Target-source choice, 2023 selection split** `[docs/source_selection_2023.csv]`
Pre-declared rule: pick NASA POWER only if its MAE vs OMI all-sky noon UVI is lower than Open-Meteo's by more than 0.3.

| Source | Reference | Subset | n | MAE | bias |
|---|---|---|---|---|---|
| Open-Meteo `uv_index` | OMI UVindex (all-sky) | all days | 275 | 2.428 | −2.339 |
| NASA POWER `nasa_uvi` | OMI UVindex (all-sky) | all days | 275 | **1.143** | −0.989 |
| Open-Meteo `uv_index_clear_sky` | TEMIS clear-sky | all days | 365 | 3.500 | −3.500 |
| NASA POWER `nasa_uvi` | TEMIS clear-sky | NASA cloud < 10 % | 71 | 2.679 | −2.679 |

→ NASA POWER chosen (difference 1.285 > 0.3).

**Training table** `[source_code/models/dataset_spec_v1.json]`: 11,156 rows (2023–2025, daytime hours with `uvi_clear ≥ 0.5`), 23 run-time features. CMF_UVI median 0.635 (p01 0.265, p99 0.874); CMF_A median 0.751; CMF_B median 0.761.

## 2. CMF model on dev 2024 (days 6–9)

**Baselines and first XGBoost** `[docs/baseline_dev_2024.csv]`

| Model | UVI MAE | R² | recall Very high | recall Extreme |
|---|---|---|---|---|
| constant CMF (train mean) | 0.703 | 0.889 | 0.631 | 0.000 |
| Open-Meteo `uv_index` (no model) | 1.252 | 0.676 | 0.591 | 0.000 |
| linear regression | 0.473 | 0.941 | 0.767 | 0.094 |
| XGBoost | 0.462 | 0.943 | 0.791 | 0.113 |

**Sample weights** `[docs/weight_experiment_dev_2024.csv]`: none 0.462 / `uvi_clear` 0.459 / `uvi_clear²` 0.461 UVI MAE → pre-declared rule selected `uvi_clear²` (differences within noise).

**Multi-output v1 (dev)** `[source_code/models/cmf_multi_xgb_v1_metrics.json]`: UVI MAE 0.461, R² 0.942, UVA MAE 2.934 W/m², UVB MAE 0.086 W/m².
**TimeSeriesSplit 5 folds, 2023–2024** `[docs/cv_folds_2023_2024.csv]`: UVI MAE 0.493 ± 0.078, UVA 3.048 ± 0.329, UVB 0.090 ± 0.011.
**Leakage checks** `[docs/leakage_checks.csv]`: 5/5 pass (no 2025 rows; no NASA/target/denominator features; folds chronological with 12-row gap; max |Spearman| 0.656; shuffled-target R² −0.105).

**Optuna (day 8)** `[source_code/models/cmf_xgb_best_params_v1.json]`, `[docs/tuning_dev_2024.csv]`

| Pre-declared rule | Value | Pass |
|---|---|---|
| CV MAE (folds 3–5) gain over default > 0.01 | 0.4579 → 0.4466 (+0.0113) | ✅ (narrowly) |
| mean alert recall drop ≤ 0.03 | 0.438 → 0.443 (no drop) | ✅ |

100 trials (42 complete, 58 pruned). Multi-output with tuned params, dev 2024 (optimistic, folds 3–5 lie in 2024): UVI MAE 0.461 → 0.450, UVA 2.934 → 2.871, UVB 0.086 → 0.084.

**Quantile regression + CQR (day 9)** `[source_code/models/cmf_uvi_quantile_xgb_v1_metrics.json]`, `[docs/quantile_alerts_cv_folds3-5.csv]`

| Pre-declared rule | Value | Pass |
|---|---|---|
| raw [q10, q90] coverage (CV folds 3–5) in [0.75, 0.85] | 0.593 | ❌ → CQR applied |
| CQR check: fold 5 coverage (Q from folds 3–4) | 0.652 → 0.863 | — |
| dev 2024 coverage with CQR (Q from 2023) | 0.578 → 0.837 | ✅ |
| lowest quantile with Extreme recall ≥ 0.8 and ≥ Very high precision ≥ 0.5 | none (q90: 0.623 / 0.596) | ❌ → q90 used (project rule) |

Alert comparison, CV folds 3–5 (≥ Very high events 704, Extreme 53):

| Quantile | ≥ Very high recall / precision / FAR | Extreme recall / precision |
|---|---|---|
| q50 | 0.839 / 0.765 / 0.060 | 0.113 / 0.600 |
| q75 | 0.926 / 0.732 / 0.079 | 0.132 / 0.500 |
| q90 (CQR) | 0.989 / 0.596 / 0.157 | 0.623 / 0.333 |

## 3. Test 2025, evaluated once (day 10)

Criteria pre-registered in commits `1641d10` / `1443ff9` before any 2025 data was read. Final CQR Q = +0.0379 (CMF) `[source_code/models/cqr_q_final_v1.json]`.
`[docs/test_2025_criteria.csv]`, `[docs/test_2025_results.json]` — **14 / 15 pass**

| # | Criterion | Value | Pass |
|---|---|---|---|
| T1 | hourly UVI MAE vs NASA POWER < 1.0 (checkpoint) | 0.479 | ✅ |
| T1b | below every baseline (const-CMF 0.708, Open-Meteo 1.244, clear-sky physics 2.471) | 0.479 | ✅ |
| T2a | noon MAE vs OMI all-sky ≤ 1.5 | 1.320 | ✅ |
| T2b | ≤ NASA POWER vs OMI + 0.3 (1.330 + 0.3) | 1.320 | ✅ |
| T2c | below every baseline vs OMI (min 1.960) | 1.320 | ✅ |
| T3a | clear-sky physics vs TEMIS (all days) ≤ 1.0 | 0.764 | ✅ |
| T3b | model vs TEMIS on clear days ≤ 1.5 | 1.360 | ✅ |
| T3c | ≤ NASA POWER vs TEMIS + 0.3 (1.580 + 0.3) | 1.360 | ✅ |
| T4 | Pearson r vs OMI irradiance ≥ 0.7 (all 4 pairs) | min 0.533 | ❌ |
| T4b | r ≥ clear-sky physics r (all pairs) | min diff +0.121 | ✅ |
| T5 | CQR interval coverage in [0.75, 0.85] | 0.806 | ✅ |
| T6a | q90 ≥ Very high recall ≥ 0.90 | 0.986 | ✅ |
| T6b | q90 ≥ Very high precision ≥ 0.50 | 0.564 | ✅ |
| T6c | q90 ≥ Very high false alarm rate ≤ 0.20 | 0.163 | ✅ |
| T6d | q90 Extreme recall ≥ 0.80 | 0.826 (19/23) | ✅ |

More from `[docs/test_2025_results.json]`: n = 3,718 hours; UVA MAE 2.910 W/m², UVB 0.088 W/m²; R² 0.934 `[source_code/models/cmf_multi_xgb_final_metrics.json]`. OMI irradiance r (model / clear-sky physics): 305 nm 0.646 / 0.525, 310 nm 0.630 / 0.436, 324 nm 0.533 / 0.313, 380 nm 0.572 / 0.203. On clear days the model is **1.359 UVI below TEMIS** (NASA POWER −1.580), while clear-sky physics is +0.831. Exact-level recall with q90: Very high 0.848, Extreme 0.826; Extreme precision 0.173 (91 false alarms).

## 4. Forecast: LSTM vs XGBoost (days 11–12)

**Baselines on the dev-2024 windows** `[docs/lstm_baseline_dev_2024.csv]`: B1 XGBoost + Open-Meteo features MAE 0.450 (≥ Very high recall 0.831); B2 Open-Meteo `uv_index` 1.162.
**LSTM, 3 seeds** `[source_code/models/lstm_v1_metrics.json]` (LSTM chosen over GRU on Nov–Dec 2023 validation loss: mean 0.00426 vs 0.00477):

| Pre-declared rule (day 11) | Value | Pass |
|---|---|---|
| dev MAE < B1 − 0.02 (0.430) | 0.463 ± 0.008 | ❌ |
| ≥ Very high recall ≥ B1 − 0.03 (0.801) | 0.873 | ✅ |

→ **XGBoost stays in the app**, including the 6–24 h forecast. LSTM bias +0.168.
**Test 2025, once, reporting only** `[docs/lstm_test_2025.json]`: LSTM 0.497 ± 0.004 vs XGBoost final 0.480, Open-Meteo 1.164; L1 (< 1.0) ✅, L2 (< XGBoost − 0.02) ❌. Refit early stopping stopped at epochs 5 / 1 / 1.

## 5. Sky CNN, separate module (days 13–14)

**Data** `[docs/sky_splits/ccsn_split.csv]`, `[docs/sky_splits/swimcat_ext_split.csv]`: CCSN 2,543 images (train/val/test 1,785 / 383 / 375; 263 images in cross-label duplicate groups; 344 in near-duplicate groups). SWIMCAT-ext 2,100 images (1,472 / 317 / 311; 1,470 in near-duplicate groups).
**Validation, 3 seeds** `[source_code/models/sky_cnn_v1_metrics.json]`: CCSN acc 0.521 / 0.518 / 0.516, UV-group 0.717 / 0.708 / 0.703, SWIMCAT-ext 0.991 / 0.984 / 0.987; colour baseline CCSN 0.314, SWIMCAT-ext per group 0.799. Exported seed 43 (lowest val loss).

**Test, once** (criteria pre-registered in `12c1828`) `[docs/sky_cnn_test.json]` — **7 / 10 pass**

| # | Criterion | Value (mean ± SD, 3 seeds) | Pass |
|---|---|---|---|
| K1 | CCSN 11-class accuracy ≥ 0.60 (conflicts removed, n 326) | 0.486 ± 0.010 | ❌ |
| K2 | CCSN macro-F1 ≥ 0.55 | 0.452 ± 0.023 | ❌ |
| K3 | CCSN 4 UV-group accuracy ≥ 0.75 | 0.685 ± 0.009 | ❌ |
| K4 | recall of high thin clouds ≥ 0.70 | 0.707 | ✅ |
| K5 | CCSN accuracy − colour baseline (0.242) ≥ 0.10 | +0.243 | ✅ |
| S1 | SWIMCAT-ext per-image accuracy ≥ 0.85 (311 images) | 0.975 ± 0.007 | ✅ |
| S2 | SWIMCAT-ext per-group accuracy ≥ 0.80 (181 groups) | 0.967 ± 0.010 | ✅ |
| S3 | per-group accuracy − colour baseline (0.818) ≥ 0.05 | +0.149 | ✅ |
| R1 | red/blue proxy: median cloud fraction of clear_sky < 0.20 | 0.001 | ✅ |
| R2 | red/blue proxy: thick_white, thick_dark, veil > 0.60 | min 0.656 | ✅ |

UV-group recall: high thin 0.707, mid 0.366, low thick 0.864, cumulus 0.413. CCSN including conflict groups (375): accuracy 0.462, macro-F1 0.438, UV-group 0.692. Red/blue medians: thin_white 0.415, patterned 0.693, thick_dark 0.969, veil 1.000.

**Cross-dataset duplicate check (day 15)** `[docs/sky_cnn_crosscheck.json]`, `[docs/sky_crossdataset_duplicates.csv]`: the day-13 rule flagged 11 CCSN × SWIMCAT-ext pairs (1 CCSN-train / SWIMCAT-test, 7 train/train, 2 train/val, 1 val/val); by visual inspection none is the same photo (low-texture look-alikes). Supplementary score without the 1 flagged test image: SWIMCAT-ext 0.975 per image, 0.967 per group (310 images / 180 groups); CCSN unchanged. Re-scoring the saved models reproduces every headline number of `sky_cnn_test.json` (checkpoint).

## 6. Limitations

1. **No ground UV instrument.** Targets are NASA POWER (satellite/model, coarse grid); validation is OMI (1° pixel, one overpass per day) and TEMIS (clear-sky only at Bangkok).
2. **Low bias on clear days, inherited from the target:** −1.36 UVI vs TEMIS on clear days (NASA POWER −1.58); noon predictions rarely exceed ~11 when TEMIS shows 12–13 `[docs/figures/test2025_noon_scatter.png]`. Warnings may understate the peak.
3. **UVA/UVB:** irradiance correlation with OMI below the 0.7 target (T4); SPECTRL2 UVB covers 300–315 nm, not 280–315 nm.
4. **Alerts:** Extreme hours are few (23 in 2025, 53 in 2024), so Extreme recall is uncertain (Wilson 95 % CI 0.63–0.93, `[source_code/notebooks/10_test_2025.ipynb]` section 4); Extreme precision is low (0.17), and ≥ Very high alerts have a 16 % false alarm rate.
5. **Dev 2024 numbers after day 8 are optimistic** (tuning folds lie in 2024); test 2025 is the unbiased estimate.
6. **Forecast covariates are Open-Meteo archive analysis, not issued forecasts**, so both LSTM and XGBoost forecast skill by lead time is overstated.
7. **Sky CNN:** CCSN genus / UV-group classification misses its criteria (K1–K3); 263 CCSN images with conflicting labels removed; SWIMCAT-ext images were "collected from Internet" (Mendeley description) with many near-duplicates, and its classes are partly separable by colour alone (baseline 0.82); cloud fraction is only a red/blue proxy (no SWIMSEG masks); no evaluation on phone photos from Pathum Thani; epoch history of seeds 42/43 lost in a sleep crash; SWIMCAT-ext used for education only.
8. **One-year test:** 2025 is a single year at a single location (Pathum Thani, 14.02 N 100.52 E).

This is an estimate for education and warning, not a medical diagnosis.
