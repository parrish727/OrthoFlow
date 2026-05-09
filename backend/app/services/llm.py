"""
LLM Abstraction Layer — swap between providers without changing business logic.

Local dev:  ollama (mistral) — fully open-source, no API keys
Production: AWS Bedrock (Claude) — HIPAA-eligible, BAA available
Custom:     Fine-tuned model on Ollama for compliance-specific tasks
"""
import httpx
from app.core.config import settings


async def complete(prompt: str, system: str = "", max_tokens: int = 4096) -> str:
    """Route to configured LLM provider."""
    if settings.LLM_PROVIDER == "ollama":
        return await _ollama(prompt, system, max_tokens)
    elif settings.LLM_PROVIDER == "bedrock":
        return await _bedrock(prompt, system, max_tokens)
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}")


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


async def _bedrock(prompt: str, system: str, max_tokens: int) -> str:
    import boto3
    import json

    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    })
    resp = client.invoke_model(modelId=settings.BEDROCK_MODEL, body=body)
    result = json.loads(resp["body"].read())
    return result["content"][0]["text"]


async def embed(text: str) -> list[float]:
    """Generate embeddings for semantic search."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.OLLAMA_URL}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
