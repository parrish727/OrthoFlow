"""Local LLM helper (Ollama) for internal classification tasks such as invoice coding.

Production text generation for user-facing AI features goes through
app/services/anthropic_gateway.py (de-identified prompts only). There is no managed-cloud model
path here by design: Ollama runs on our own hardware.
"""
import httpx
from app.core.config import settings


async def complete(prompt: str, system: str = "", max_tokens: int = 4096) -> str:
    """Run a prompt on the local Ollama model."""
    if settings.LLM_PROVIDER != "ollama":
        raise ValueError(f"Unsupported LLM_PROVIDER for local completion: {settings.LLM_PROVIDER}")
    return await _ollama(prompt, system, max_tokens)


async def _ollama(prompt: str, system: str, max_tokens: int) -> str:
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
        )
        resp.raise_for_status()
        return resp.json()["response"]
