"""LLM client factory -- one place every node/guardrail gets a model from.

Mirrors the pattern used in the sibling AgentFlow Studio repo: LangChain's
provider-agnostic `init_chat_model`, cached per-temperature. Backed by a
local Ollama model rather than a hosted API -- this project makes several
small LLM calls per turn (classify, compose, injection check, faithfulness
judge) and CI runs the full golden set on every PR, so "free and local"
beats "fast and metered" here. Swapping to a hosted provider later is a
one-line change to `GUARDIAN_LLM_MODEL` (e.g. "groq:llama-3.3-70b-versatile"),
since `init_chat_model` itself doesn't care which provider the string names.
"""

from __future__ import annotations

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings


@lru_cache
def get_llm(temperature: float = 0.0) -> BaseChatModel:
    settings = get_settings()
    return init_chat_model(
        settings.llm_model,
        temperature=temperature,
        base_url=settings.ollama_base_url,
    )


def call_llm_text(prompt: str, *, temperature: float = 0.0) -> str:
    """Plain prompt-in/text-out helper -- what LLMJudge and guardrail
    classifiers need, without every caller touching LangChain message types."""
    response = get_llm(temperature=temperature).invoke(prompt)
    return response.content if isinstance(response.content, str) else str(response.content)
