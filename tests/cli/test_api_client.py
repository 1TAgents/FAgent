import pytest
import httpx

from src.cli.api_client import BackendClient


@pytest.mark.asyncio
async def test_send_non_stream_uses_backend_detail_on_error():
    def handler(request):
        return httpx.Response(403, json={"detail": "No access to this conversation"})

    client = BackendClient(
        base_url="http://backend.test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="No access to this conversation"):
        await client.send_non_stream(cid=1, message="hello")


@pytest.mark.asyncio
async def test_create_session_success_with_mock_transport():
    def handler(request):
        assert request.url.path == "/api/chat/session/create"
        return httpx.Response(200, json={"cid": 7})

    client = BackendClient(
        base_url="http://backend.test",
        transport=httpx.MockTransport(handler),
    )

    assert await client.create_session(title="test") == 7
