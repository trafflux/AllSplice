import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from ai_gateway.middleware.correlation import (
    CorrelationIdMiddleware,
    get_request_id,
    request_id_dependency,
)


@pytest.fixture()
def app_with_corr_id() -> FastAPI:
    app = FastAPI()

    # Install middleware
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/echo-id")
    async def echo_id(dep_id: str | None = Depends(request_id_dependency)) -> dict[str, str | None]:
        # Validate dependency getter is same as direct utility
        assert dep_id == get_request_id()
        return {"request_id": dep_id}

    return app


@pytest.mark.anyio
async def test_generates_request_id_when_missing_header(app_with_corr_id: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_with_corr_id), base_url="http://test"
    ) as client:
        res = await client.get("/echo-id")
        assert res.status_code == 200
        body = res.json()
        rid_body = body.get("request_id")
        rid_header = res.headers.get("X-Request-ID")
        assert isinstance(rid_header, str) and len(rid_header) > 0
        assert rid_body == rid_header


@pytest.mark.anyio
async def test_preserves_incoming_request_id_header(app_with_corr_id: FastAPI) -> None:
    incoming = "abc-123"
    async with AsyncClient(
        transport=ASGITransport(app=app_with_corr_id), base_url="http://test"
    ) as client:
        res = await client.get("/echo-id", headers={"X-Request-ID": incoming})
        assert res.status_code == 200
        body = res.json()
        assert body["request_id"] == incoming
        assert res.headers.get("X-Request-ID") == incoming


@pytest.mark.anyio
async def test_isolated_context_between_requests(app_with_corr_id: FastAPI) -> None:
    # Ensure contextvar isolation across requests
    async with AsyncClient(
        transport=ASGITransport(app=app_with_corr_id), base_url="http://test"
    ) as client:
        res1 = await client.get("/echo-id")
        res2 = await client.get("/echo-id")
        assert res1.json()["request_id"] != res2.json()["request_id"]
