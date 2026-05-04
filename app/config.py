"""Centralised configuration loaded from environment variables / .env file."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    temporal_host: str
    temporal_namespace: str
    task_queue: str
    # LLM
    llm_provider: str          # openai | anthropic | ollama
    openai_api_key: str
    anthropic_api_key: str
    llm_model: str
    ollama_base_url: str       # default: http://localhost:11434/v1
    llm_json_max_retries: int  # parse retries before raising to Temporal
    # Paths
    cases_dir: str
    outputs_dir: str


def load_config() -> Config:
    return Config(
        temporal_host=os.getenv("TEMPORAL_HOST", "localhost:7233"),
        temporal_namespace=os.getenv("TEMPORAL_NAMESPACE", "default"),
        task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "rtl-debug-queue"),
        llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "qwen2.5-coder:7b"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        llm_json_max_retries=int(os.getenv("LLM_JSON_MAX_RETRIES", "3")),
        cases_dir=os.getenv("CASES_DIR", "cases"),
        outputs_dir=os.getenv("OUTPUTS_DIR", "outputs"),
    )


config = load_config()
