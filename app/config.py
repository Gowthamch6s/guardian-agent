"""Central settings, read once via `get_settings()`.

Kept as one pydantic-settings object (mirrors AgentFlow Studio's app/config.py
pattern) so every module reads limits and model names from one place instead
of scattering magic numbers through guardrail code.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Ollama, not a hosted API: every guardrail/classifier call here is a
    # small, frequent LLM call (intent classification, injection check,
    # faithfulness judge...), and CI runs the whole golden set on every PR --
    # a free local model means no API key, no per-call cost, ever, for
    # anyone who clones this repo. `ollama_base_url` only matters if Ollama
    # isn't reachable at its default localhost port (e.g. a CI container).
    llm_model: str = Field("ollama:llama3.2", alias="GUARDIAN_LLM_MODEL")
    ollama_base_url: str = Field("http://localhost:11434", alias="GUARDIAN_OLLAMA_BASE_URL")
    mlflow_tracking_uri: str = Field("sqlite:///mlflow.db", alias="GUARDIAN_MLFLOW_TRACKING_URI")
    mlflow_experiment_name: str = Field("guardian-agent", alias="GUARDIAN_MLFLOW_EXPERIMENT_NAME")

    # Deterministic policy thresholds -- business rules, not model judgment.
    refund_auto_approve_limit_usd: float = Field(250.0, alias="GUARDIAN_REFUND_AUTO_APPROVE_LIMIT_USD")
    card_freeze_always_needs_approval: bool = Field(True, alias="GUARDIAN_CARD_FREEZE_ALWAYS_NEEDS_APPROVAL")
    update_contact_always_needs_approval: bool = Field(
        True, alias="GUARDIAN_UPDATE_CONTACT_ALWAYS_NEEDS_APPROVAL"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
