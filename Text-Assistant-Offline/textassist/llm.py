"""Runs GGUF models locally with llama.cpp. No network access."""
import threading

from .config import MODELS, Settings


class ModelNotFound(RuntimeError):
    pass


class LocalLLM:
    """Loads models lazily and keeps them in memory between calls."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._loaded: dict[str, object] = {}
        self._lock = threading.Lock()  # llama.cpp contexts are not thread-safe

    def available(self, key: str) -> bool:
        return self.settings.has_model(key)

    def _load(self, key: str):
        if key in self._loaded:
            return self._loaded[key]
        path = self.settings.model_path(key)
        if not path.is_file():
            raise ModelNotFound(
                f"Model file not found: {path}\nRun once while online:  python download_models.py"
            )
        from llama_cpp import Llama  # imported here so tests run without it

        if self.settings.low_memory:
            self._loaded.clear()
        llm = Llama(
            model_path=str(path),
            n_ctx=self.settings.n_ctx,
            n_threads=self.settings.n_threads,
            n_gpu_layers=self.settings.n_gpu_layers,
            chat_format=MODELS[key].chat_format,
            seed=self.settings.seed,
            verbose=False,
        )
        self._loaded[key] = llm
        return llm

    def chat(self, key: str, messages: list[dict], max_tokens: int = 1024,
             temperature: float | None = None) -> str:
        with self._lock:
            llm = self._load(key)
            out = llm.create_chat_completion(
                messages=messages,
                temperature=self.settings.temperature if temperature is None else temperature,
                top_p=0.9,
                repeat_penalty=1.05,
                max_tokens=max_tokens,
            )
        return out["choices"][0]["message"]["content"] or ""
