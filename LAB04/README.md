# ML-4-KNN — k-Nearest Neighbor & Its Applications on US COVID-19 County Data

This project demonstrates the **k-Nearest Neighbor (KNN)** algorithm and its two
main applications — **supervised classification** and, combined with **K-Means**,
**unsupervised clustering** — implemented directly with **TensorFlow tensor
operations** (no scikit-learn model code), applied to the New York Times
US-counties COVID-19 dataset.

## Repository structure

```
ML-4-KNN/
│
├── data-covid/
│   └── us_counties_dataset.csv        # engineered, one row per county
│
├── classification/                    # Application 1: KNN classification
│   ├── main.py                        # pipeline: split -> tune k -> evaluate
│   ├── data_loader.py                 # load, feature-select, split, scale
│   ├── knn_tf.py                      # KNN classifier (pure TensorFlow ops)
│   ├── evaluate.py                    # accuracy, confusion matrix, plots
│   └── outputs/
│       ├── 01_k_curve.png             # validation accuracy vs k
│       ├── 02_confusion_matrix.png    # test-set confusion matrix
│       └── predictions.csv            # per-county test predictions
│
├── clustering/                        # Application 2: KNN-assisted clustering
│   ├── main.py                        # pipeline: elbow -> fit -> project -> save
│   ├── data_loader.py                 # load, feature-select, scale
│   ├── kmeans_tf.py                   # K-Means (pure TensorFlow ops, k-means++)
│   ├── knn_tools.py                   # KNN-vote labeling + cohesion scoring
│   ├── visualize.py                   # elbow plot, PCA cluster scatter plot
│   └── outputs/
│       ├── 01_elbow.png               # inertia vs k
│       ├── 02_clusters.png            # PCA-projected cluster scatter
│       ├── cluster_summary.csv        # per-cluster aggregate stats
│       └── clustered_animals.csv      # every county + assigned cluster
│
├── requirements.txt
└── link-data.txt                      # source of the raw dataset
```

> Note: `clustered_animals.csv` keeps that filename from the course/project
> template this repo follows; its content is the **clustered county data**
> (`data-covid` counties, not animals).

## Dataset & feature engineering

**Raw source**: `us-counties.csv` from the NYT COVID-19 data repository — a
daily, cumulative cases/deaths time series per US county (~2.5M rows,
2020‑01‑21 to 2022‑05‑13). See `link-data.txt`.

Because the raw file is a long daily time series, it was **aggregated to one
row per county** (`data-covid/us_counties_dataset.csv`, 3,139 counties after
filtering out counties with < 50 total cases and "Unknown" county rows) with
these engineered features:

| Column                    | Meaning                                                     |
|----------------------------|--------------------------------------------------------------|
| `total_cases`              | Cumulative confirmed cases at end of series                  |
| `total_deaths`             | Cumulative deaths at end of series                            |
| `death_rate_pct`           | `total_deaths / total_cases * 100`                            |
| `duration_days`            | Days between first and last recorded case                     |
| `peak_daily_new_cases`     | Highest single-day new-case count                              |
| `avg_daily_new_cases`      | Mean daily new cases over the recorded period                  |
| `std_daily_new_cases`      | Std. dev. of daily new cases (volatility of the outbreak)      |
| `case_growth_rate`         | `total_cases / duration_days` (average cases per day)          |
| `risk_level`                | **Classification target** — Low / Medium / High, from tertiles of `death_rate_pct` |

## Application 1 — KNN Classification

**Task**: predict a county's `risk_level` (Low / Medium / High, based on its
COVID-19 death rate) from *other* outbreak-shape features (`total_cases`,
`total_deaths`, `duration_days`, `peak_daily_new_cases`, `avg_daily_new_cases`,
`std_daily_new_cases`, `case_growth_rate`) — **excluding `death_rate_pct`
itself**, since the target was derived from it and using it would leak the
answer.

**Method** (`classification/knn_tf.py`): a fully vectorized TensorFlow KNN —
pairwise squared Euclidean distance via `‖a-b‖² = ‖a‖² + ‖b‖² - 2a·b`
(`tf.matmul`), `tf.math.top_k` to find the k nearest neighbors, then majority
vote via `tf.one_hot` + `tf.reduce_sum`.

**Pipeline** (`classification/main.py`):
1. Split counties 60% train / 20% validation / 20% test (fixed seed).
2. Standardize features (z-score, fit on train only).
3. Sweep `k = 1..25` on the **validation** split only, pick the best `k`
   (avoids tuning on the test set).
4. Evaluate once on the held-out **test** split, save the confusion matrix
   and per-county `predictions.csv`.

**Results** (test set, k chosen on validation):
- Best k ≈ 1 (nearest single neighbor generalizes best on this feature set)
- Test accuracy ≈ **0.65**
- Per-class F1: Low ≈ 0.68, Medium ≈ 0.59, High ≈ 0.70 — the model separates
  "Low" and "High" risk counties better than the middle "Medium" band, which
  is expected since tertile boundaries make Medium harder to distinguish
  from its neighbors.

## Application 2 — K-Means Clustering (with KNN as a supporting tool)

**Task**: group counties into clusters that share a similar overall
outbreak *profile* (size, severity, growth pattern) — this time using
`death_rate_pct` as a normal input feature (no target leakage concern,
since clustering is unsupervised).

**Method**:
- `clustering/kmeans_tf.py` — K-Means (Lloyd's algorithm) written directly
  in TensorFlow ops, using k-means++ seeding for stable initialization.
- `clustering/knn_tools.py` — KNN used as a *clustering utility*, not just a
  classifier:
  - `label_new_points()` — assigns brand-new/unseen counties to a cluster by
    KNN-majority-vote among already-clustered counties (an inductive
    alternative to "nearest centroid").
  - `cluster_cohesion()` — for every county, the average distance to its
    k nearest neighbors *within the same cluster*, used as a simple
    density/tightness score per county.

**Pipeline** (`clustering/main.py`):
1. Standardize features, sweep `k = 1..10`, save the elbow plot.
2. Fit final K-Means at the chosen `k = 4`.
3. Score cohesion with `knn_tools`, sanity-check KNN-vote vs K-Means
   agreement on a demo sample of "new" points.
4. Project to 2D with PCA (implemented via `numpy.linalg.svd`, no
   scikit-learn) and plot the clusters.
5. Save `cluster_summary.csv` (per-cluster stats) and
   `clustered_animals.csv` (every county + its cluster id + cohesion score).

**Resulting clusters** (`k=4`, see `clustering/outputs/cluster_summary.csv`):

| Cluster | # counties | Avg. total cases | Avg. death rate % | Profile |
|---------|-----------:|------------------:|-------------------:|---------|
| 0 | 134 | ~223,700 | 1.13% | Large metro counties, high case volume |
| 1 | 6   | ~1,408,800 | 1.05% | Extreme outliers — the biggest US counties (LA, Maricopa, Miami‑Dade, Cook, Harris, San Diego) |
| 2 | 2,063 | ~16,800 | 1.20% | Typical mid/small counties — the bulk of the country |
| 3 | 936 | ~6,100 | 2.35% | Smaller counties with disproportionately **higher** death rates |

## How to run

```bash
pip install -r requirements.txt

cd classification && python main.py
cd ../clustering    && python main.py
```

Both scripts are self-contained: they load `data-covid/us_counties_dataset.csv`,
run the full pipeline, print metrics to the console, and write all plots/CSVs
into their respective `outputs/` folders.

## Report

See `report.pdf` for the full written report (methodology, results, and
discussion) and `dataset.csv` for the flat county-level dataset used by
both applications.
