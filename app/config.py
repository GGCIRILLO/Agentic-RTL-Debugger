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
    llm_provider: str
    openai_api_key: str
    anthropic_api_key: str
    llm_model: str
    cases_dir: str
    outputs_dir: str


def load_config() -> Config:
    return Config(
        temporal_host=os.getenv("TEMPORAL_HOST", "localhost:7233"),
        temporal_namespace=os.getenv("TEMPORAL_NAMESPACE", "default"),
        task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "rtl-debug-queue"),
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o"),
        cases_dir=os.getenv("CASES_DIR", "cases"),
        outputs_dir=os.getenv("OUTPUTS_DIR", "outputs"),
    )


config = load_config()
