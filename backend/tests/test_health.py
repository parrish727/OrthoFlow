import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app():
    """Import app inside fixture to control env."""
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql://orthoflow:testpass@localhost:5432/orthoflow_test")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("LLM_PROVIDER", "ollama")
    os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")
    from app.main import app
    return app


@pytest.mark.asyncio
async def test_health(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["ready"] is True
