"""LLM registry and backend adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class BaseLlm(Protocol):
    async def generate(self, *, persona_prompt: str, query: str, evidence: list) -> str:
        ...


@dataclass
class GeminiBackend:
    model_name: str

    async def generate(self, *, persona_prompt: str, query: str, evidence: list) -> str:
        _ = persona_prompt
        _ = evidence
        return f"{query}"


@dataclass
class NovaLiteBackend:
    model_name: str = "nova-lite-v2"

    async def generate(self, *, persona_prompt: str, query: str, evidence: list) -> str:
        if evidence:
            return f"{query} [^1]"
        return f"{query}"


class LLMRegistry:
    _models: dict[str, BaseLlm] = {}

    @classmethod
    def register(cls, model: str, backend: BaseLlm) -> None:
        cls._models[model] = backend

    @classmethod
    def resolve(cls, model: str) -> BaseLlm:
        if model not in cls._models:
            raise KeyError(f"Unknown model '{model}'")
        return cls._models[model]

    @classmethod
    def init_defaults(cls) -> None:
        if "gemini-2.5-flash" not in cls._models:
            cls.register("gemini-2.5-flash", GeminiBackend("gemini-2.5-flash"))
        if "nova-lite-v2" not in cls._models:
            cls.register("nova-lite-v2", NovaLiteBackend())
