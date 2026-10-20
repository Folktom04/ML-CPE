"""Settings and the list of local models."""
import os
from dataclasses import dataclass, field
from pathlib import Path

# Never reach the network at runtime.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

PROJECT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ModelSpec:
    key: str
    repo: str          # Hugging Face repo, used only by download_models.py
    filename: str
    size_gb: float
    chat_format: str | None = None  # None = use the template stored in the GGUF
    note: str = ""


MODELS: dict[str, ModelSpec] = {
    # General Thai model: spell check, tone rewriting, translation to other languages.
    "general": ModelSpec(
        key="general",
        repo="typhoon-ai/typhoon2.1-gemma3-4b-gguf",
        filename="typhoon2.1-gemma3-4b-q4_k_m.gguf",
        size_gb=2.5,
        note="Typhoon 2.1 (Gemma 3 4B) - Thai-tuned chat model",
    ),
    # Larger general model for better quality on machines with 16 GB+ RAM.
    "general-large": ModelSpec(
        key="general-large",
        repo="typhoon-ai/typhoon2.1-gemma3-12b-gguf",
        filename="typhoon2.1-gemma3-12b-q4_k_m.gguf",
        size_gb=7.3,
        note="Typhoon 2.1 (Gemma 3 12B) - slower, more accurate",
    ),
    # Dedicated Thai <-> English translator.
    "translate": ModelSpec(
        key="translate",
        repo="typhoon-ai/typhoon-translate1.5-4b-gguf",
        filename="typhoon-translate1.5-4b-q4_k_m.gguf",
        size_gb=2.5,
        chat_format="chatml",  # the GGUF has no template; the base model is Qwen3
        note="Typhoon Translate 1.5 - Thai <-> English",
    ),
}


@dataclass
class Settings:
    model_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("TEXTASSIST_MODEL_DIR", PROJECT_DIR / "models"))
    )
    # Which entry of MODELS is used as the general model.
    general_model: str = field(default_factory=lambda: os.environ.get("TEXTASSIST_GENERAL", "general"))
    n_ctx: int = int(os.environ.get("TEXTASSIST_CTX", "4096"))
    n_threads: int | None = int(os.environ["TEXTASSIST_THREADS"]) if os.environ.get("TEXTASSIST_THREADS") else None
    n_gpu_layers: int = int(os.environ.get("TEXTASSIST_GPU_LAYERS", "0"))  # -1 = all layers on GPU
    temperature: float = 0.1
    seed: int = 42
    # Keep only one model in RAM at a time (saves ~2.5 GB, slower when switching tasks).
    low_memory: bool = os.environ.get("TEXTASSIST_LOW_MEMORY", "0") == "1"

    def model_path(self, key: str) -> Path:
        return self.model_dir / MODELS[key].filename

    def has_model(self, key: str) -> bool:
        return self.model_path(key).is_file()
