---
trigger: glob
globs: "**/*.py, **/*.ipynb"
---

# Python / ML conventions

- Format with black (line length 100) and sort imports with isort. Type-hint all public functions.
- Use `pathlib.Path` for paths, relative to the project root `Final-Project/` (from `source_code/src/*.py` that is `ROOT = Path(__file__).resolve().parents[2]`; data lives in `ROOT / "dataset"`).
- Timestamps: store in UTC, convert to Asia/Bangkok only for display.
- Set `random_state=42` / `tf.random.set_seed(42)` everywhere for reproducibility.
- Save models with a version suffix (`source_code/models/cmf_xgb_v1.json`) and write a matching `*_metrics.json` (MAE, RMSE, R², fold scores, date, feature list).
- Report metrics on the UVI scale (clear_sky × predicted CMF), not only on CMF.
- For classification of WHO levels, always print the confusion matrix and the recall of levels สูงมาก and รุนแรงมาก.
- API calls: add retries with backoff, cache raw responses to `dataset/raw/`, never re-download what already exists.
- Plots: matplotlib, axes labelled with units (UVI, W/m², %), saved to `docs/figures/` as PNG at 150 dpi.
