"""Model API configuration loader based on YAML files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODELS_DIR = PROJECT_ROOT / "assets" / "models"
DEFAULT_MODEL_CONFIG = "deepseek-chat.yaml"


class APIConfigError(RuntimeError):
    """Raised when model API YAML config cannot be loaded or validated."""


@dataclass(frozen=True)
class ModelAPIConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    timeout_seconds: float = 90.0
    chat_completions_path: str = "/chat/completions"
    default_temperature: float = 0.2
    headers: dict[str, str] | None = None

    @property
    def endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.chat_completions_path}"


def _import_yaml_module() -> Any:
    try:
        import yaml  # type: ignore[import-untyped]
    except Exception as exc:  # pragma: no cover - depends on local env
        raise APIConfigError(
            "PyYAML is required to load model configs. Install with: pip install pyyaml"
        ) from exc
    return yaml


def list_model_configs(models_dir: Path | None = None) -> list[str]:
    base_dir = models_dir or DEFAULT_MODELS_DIR
    if not base_dir.exists():
        return []
    names: list[str] = []
    for path in sorted(base_dir.glob("*.yaml")):
        names.append(path.name)
    for path in sorted(base_dir.glob("*.yml")):
        names.append(path.name)
    return sorted(set(names))


def _resolve_config_path(
    config: str | None,
    models_dir: Path | None = None,
) -> Path:
    base_dir = models_dir or DEFAULT_MODELS_DIR

    candidate = (config or "").strip() or os.getenv("PARADOX_MODEL_CONFIG", "").strip()
    if candidate:
        raw = Path(candidate).expanduser()
        if raw.is_file():
            return raw

        normalized = candidate
        if not normalized.endswith((".yaml", ".yml")):
            normalized = f"{normalized}.yaml"
        name_path = base_dir / normalized
        if name_path.is_file():
            return name_path

        raise APIConfigError(
            f"Model config not found: {candidate}. "
            f"Try one of: {', '.join(list_model_configs(base_dir)) or 'N/A'}"
        )

    default_path = base_dir / DEFAULT_MODEL_CONFIG
    if default_path.is_file():
        return default_path

    configs = list_model_configs(base_dir)
    if not configs:
        raise APIConfigError(
            f"No model YAML found under {base_dir}. "
            "Create a config like assets/models/deepseek-chat.yaml."
        )
    return base_dir / configs[0]


def load_model_config(
    config: str | None = None,
    models_dir: Path | None = None,
) -> ModelAPIConfig:
    path = _resolve_config_path(config=config, models_dir=models_dir)
    yaml = _import_yaml_module()

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise APIConfigError(f"Failed to read model config YAML: {path}") from exc

    if not isinstance(data, dict):
        raise APIConfigError(f"Invalid YAML object in {path}: expected mapping at root.")

    provider = str(data.get("provider", "")).strip()
    model = str(data.get("model", "")).strip()
    base_url = str(data.get("base_url", "")).strip()
    if not provider or not model or not base_url:
        raise APIConfigError(
            f"Invalid config {path}: provider/model/base_url are required."
        )

    api_key_env = str(data.get("api_key_env", "")).strip()
    inline_key = str(data.get("api_key", "")).strip()
    api_key = os.getenv(api_key_env, "").strip() if api_key_env else ""
    if not api_key:
        api_key = inline_key
    if not api_key:
        hint = f"env {api_key_env}" if api_key_env else "api_key"
        raise APIConfigError(
            f"API key is empty for {path}. Set {hint} or fill api_key in YAML."
        )

    chat_path = str(data.get("chat_completions_path", "/chat/completions")).strip()
    if not chat_path.startswith("/"):
        chat_path = f"/{chat_path}"

    timeout_seconds = float(data.get("timeout_seconds", 90))
    default_temperature = float(data.get("default_temperature", 0.2))

    raw_headers = data.get("headers")
    headers: dict[str, str] = {}
    if isinstance(raw_headers, dict):
        for key, value in raw_headers.items():
            key_text = str(key).strip()
            value_text = str(value).strip()
            if key_text and value_text:
                headers[key_text] = value_text
    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    return ModelAPIConfig(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        chat_completions_path=chat_path,
        default_temperature=default_temperature,
        headers=headers,
    )

