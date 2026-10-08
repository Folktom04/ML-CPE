# Himawari experiment: amendments to the pre-registration

Pre-registration: `source_code/models/sat_exp_prereg_v1.json`, committed in `f4f625e`
(2026-10-08 01:04 +0700). The dev result (`docs/sat_dev_results.json`, decision **go**) was committed
in `179cf5d`. The prereg file itself is not edited; amendments are recorded here.

## Amendment 1: process only (proposed 2026-10-08, after the dev result, before `--refit` / `--test`)

**Not changed:** features, feature definitions, rows, training (models, params, seeds, weights,
CQR), metrics, bootstrap, test period and the criteria D1-D4 / P1-P4. The decision on dev is not
re-run. No 2026 target has been read.

**Why:** reading the code before `--refit` showed three process risks for the one-time 2026 test:

1. The refit manifest names the model files but does not record their content. A model file
   could change between `--refit` and `--test` without anyone noticing.
2. `--test` writes the lock first and then downloads NASA POWER, OMI (needs an Earthdata login)
   and TEMIS between the scoring steps. If the network or the login failed after the lock, the
   test set would be "opened" with no result and no allowed way to finish. The only way out
   would be to delete the lock by hand, which breaks the one-time rule.
3. Access problems (login, servers, low memory) could only be found by running `--test`
   itself, which opens 2026.

**Changes:**

| | Change | Files |
|---|---|---|
| a | `refit_manifest.json` records the SHA-256 of every model file (`multi_sha256`, `quantile_sha256`). `--test` checks every hash **before** writing the lock and refuses on a mismatch or missing file. | `src/sat_experiment.py` (`file_sha256`, `save_refit_models`, `verify_model_hashes`) |
| b | After the lock, `--test` first saves all 2026 targets to disk (NASA POWER raw cache, OMI pixel cache + `omi_holdout_2026.csv`, `temis_holdout_2026.csv`), marks `targets_downloaded_utc` in the lock, and only then evaluates from disk. A crashed run can be continued with `--resume-test` only if (1) the lock exists, (2) HEAD is the commit recorded in the lock, (3) every guarded file equals HEAD and (4) there is no results file. The results file is written atomically (temp file + rename) after everything has succeeded, and its presence always refuses `--test` and `--resume-test`, so 2026 is never evaluated twice. Each resume is logged in the lock (`resumed_utc`). | `src/splits.py` (`open_test_2026(resume=...)`, `update_lock`), `src/sat_experiment.py` (`download_targets_2026`, `test_main(resume)`) |
| c | New `--preflight` checks, without touching 2026: guarded files + manifest + dev results equal HEAD; no lock and no results; model hashes; Earthdata login; one OMI day of the opened year 2025 (search, download to a temp folder, pixel read, file deleted, no value printed); NASA POWER for the same 2025 day; TEMIS server reachable (HEAD request); at least 4 GB free memory. | `src/sat_experiment.py` (`preflight`), `src/fetch_validation.py` (`earthdata_login`, `probe_omi`) |
| d | This file. | `docs/sat_exp_amendments.md` |

**Additions approved with amendment 1 (2026-10-08, still process only):**

| | Change | Files |
|---|---|---|
| e | `--test` and `--resume-test` refuse to run if any **tracked** file under `source_code/src` or `source_code/models` has unstaged or staged changes, not only the guarded files (`git status --porcelain --untracked-files=no`). Untracked or ignored files (the refit models) are checked by SHA-256 instead. | `src/splits.py` (`assert_clean_paths`), `src/sat_experiment.py` (`test_main`) |
| f | When the test is opened, the lock records the SHA-256 of every input file `--test` reads (`inputs_sha256`): satellite series, Open-Meteo weather 2023-2025 and 2026 H1, air quality 2026 H1, `train_sat.parquet`, ozone climatology, the B_main model files + CQR Q, and `dataset_spec_sat_v1.json`. `--resume-test` recomputes them and refuses on any difference. | `src/splits.py` (`open_test_2026(extra=...)`), `src/sat_experiment.py` (`test_inputs`, `input_hashes`) |
| g | `.gitignore`: `source_code/models/sat_exp/*.joblib` and `source_code/models/sat_exp/*.ubj.gz` (~0.5 GB of refit models; their SHA-256 values are in the committed `refit_manifest.json`). Checked with `git check-ignore`. | `.gitignore` |
| h | psutil is in `.venv` only as a dependency of ipykernel/ipython and is not in `requirements.txt`, so it is not used and nothing was installed. Free memory comes from `GlobalMemoryStatusEx` (ctypes) on Windows or `os.sysconf` on POSIX. The memory check in `--preflight` is a **warning**, not a failure. | `src/sat_experiment.py` (`free_memory_gb`, `preflight`) |

`fetch_omi` now calls the shared `earthdata_login()`. The behaviour is the same: credentials come
from `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD` in the environment after
`load_dotenv(ROOT / ".env")`.

**Order after approval:** commit amendment 1, then `--refit` (manifest with hashes), commit
`refit_manifest.json`, then `--preflight`, then `--test` once (`--resume-test` only after a crash).
