"""Download the model files once (needs internet). After this the system runs fully offline.

    python download_models.py                 # general (4B) + translate models, ~5 GB
    python download_models.py --large         # also the 12B general model, +7.3 GB
    python download_models.py --only general  # just one model
"""
import argparse
import os
import sys

# This script is the only part that goes online.
os.environ["HF_HUB_OFFLINE"] = "0"

from textassist.config import MODELS, Settings  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--large", action="store_true", help="also download the 12B general model")
    ap.add_argument("--only", choices=list(MODELS), action="append", help="download only these models")
    args = ap.parse_args()

    keys = args.only or (["general", "translate"] + (["general-large"] if args.large else []))
    settings = Settings()
    settings.model_dir.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("Install first:  pip install huggingface_hub")
        return 1

    for key in keys:
        spec = MODELS[key]
        dest = settings.model_path(key)
        if dest.is_file():
            print(f"[ok] {key}: already at {dest}")
            continue
        print(f"[..] {key}: downloading {spec.filename} (~{spec.size_gb} GB) from {spec.repo}")
        hf_hub_download(repo_id=spec.repo, filename=spec.filename, local_dir=settings.model_dir)
        print(f"[ok] {key}: saved to {dest}")

    print("\nDone. You can now disconnect from the internet and run:  python app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
