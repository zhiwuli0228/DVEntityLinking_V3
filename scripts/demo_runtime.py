from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def ensure_src_path() -> None:
    src_text = str(SRC)
    if src_text not in sys.path:
        sys.path.insert(0, src_text)


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return ROOT / candidate


def setup_logging(log_dir: str | Path, name: str) -> tuple[logging.Logger, Path]:
    log_path = resolve_path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_path / f"{name}-{timestamp}.log"

    logger = logging.getLogger("dv_entity_linking.demo")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(file_handler)

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.addHandler(console)
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.propagate = False

    return logger, log_file


def load_llm_config(config_path: str | Path, logger: logging.Logger):
    ensure_src_path()
    from dv_entity_linking.llm import LLMConfig

    resolved = resolve_path(config_path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    api_key_env = str(payload.get("api_key_env", "DVEL_LLM_API_KEY"))
    env_name_like = re.fullmatch(r"[A-Z_][A-Z0-9_]*", api_key_env) is not None
    if not os.getenv(api_key_env) and api_key_env and not env_name_like:
        os.environ["DVEL_LLM_API_KEY"] = api_key_env
        payload["api_key_env"] = "DVEL_LLM_API_KEY"
        logger.warning(
            "api_key_env looks like a key value. Using a process-local "
            "DVEL_LLM_API_KEY value for this run; move the key to an "
            "environment variable for durable use."
        )
    return LLMConfig(
        provider=str(payload.get("provider", "openai_compatible")),
        enabled=bool(payload.get("enabled", False)),
        model=str(payload.get("model", "qwen3.6-27b")),
        base_url=str(payload.get("base_url", "")),
        api_key_env=str(payload.get("api_key_env", "DVEL_LLM_API_KEY")),
        timeout_seconds=float(payload.get("timeout_seconds", 20.0)),
    )


def allowed_layers_for_catalog(catalog_path: str | Path) -> list[str] | None:
    resolved = resolve_path(catalog_path)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    metadata = payload.get("metadata") if isinstance(payload, dict) else None
    if not isinstance(metadata, dict):
        return None
    if metadata.get("schema_version") in {"v1.alarm_entity.1", "v1.alarm_entity.2"}:
        return ["L1_SANITIZED"]
    return None


def build_service(
    *,
    catalog_path: str | Path,
    mode: str,
    llm_config_path: str | Path,
    logger: logging.Logger,
    storage_mode: str = "legacy_catalog",
    gauss_mock_path: str | Path = "samples/real/v3_gauss_entities.json",
    redis_mock_path: str | Path = "samples/real/v3_redis_entity_words.json",
):
    ensure_src_path()
    from dv_entity_linking.catalog import CatalogRepository
    from dv_entity_linking.llm import OpenAICompatibleLLMClient
    from dv_entity_linking.models import RunMode
    from dv_entity_linking.service import EntityLinkingService

    run_mode = RunMode(mode)
    if storage_mode == "v3_mock":
        service = EntityLinkingService.from_v3_mock(
            gauss_mock_path=resolve_path(gauss_mock_path),
            redis_mock_path=resolve_path(redis_mock_path),
        )
        load_result = service.catalog.load()
        logger.info(
            "Loaded V3 mock storage: entity_count=%s word_count=%s",
            load_result.entity_count,
            service.v3_pipeline.storage_repository.startup_report.word_count
            if service.v3_pipeline
            else 0,
        )
    else:
        catalog = CatalogRepository(
            resolve_path(catalog_path),
            allowed_data_layers=allowed_layers_for_catalog(catalog_path),
        )
        load_result = catalog.load()
        logger.info("Loaded catalog: entity_count=%s", load_result.entity_count)
        service = EntityLinkingService(catalog)

    llm_client = None
    if run_mode == RunMode.LLM_ENABLED_DEMO:
        llm_config = load_llm_config(llm_config_path, logger)
        llm_client = OpenAICompatibleLLMClient(llm_config)
        logger.info("LLM client enabled: provider=%s model=%s", llm_config.provider, llm_config.model)
    else:
        logger.info("LLM client disabled: mode=%s", run_mode.value)

    service.configure_llm_client(llm_client)
    return service, run_mode
