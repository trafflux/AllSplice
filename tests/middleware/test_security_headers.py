import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ai_gateway.middleware.security_headers import (
    DEFAULT_SECURITY_HEADERS,
    SecurityHeadersMiddleware,
)


@pytest.fixture()
def app_enabled() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, enabled=True)

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.fixture()
def app_disabled() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, enabled=False)

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.mark.anyio
async def test_security_headers_present_when_enabled(app_enabled: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_enabled), base_url="http://test"
    ) as client:
        res = await client.get("/ok")
        assert res.status_code == 200
        for k, v in DEFAULT_SECURITY_HEADERS.items():
            assert res.headers.get(k) == v


@pytest.mark.anyio
async def test_security_headers_absent_when_disabled(app_disabled: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_disabled), base_url="http://test"
    ) as client:
        res = await client.get("/ok")
        assert res.status_code == 200
        for k in DEFAULT_SECURITY_HEADERS:
            assert res.headers.get(k) is None
