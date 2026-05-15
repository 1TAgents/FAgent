"""
Backend API Client

Handles HTTP communication with the FAgent backend service.
"""
import os
import json
from typing import Optional, AsyncGenerator
import httpx

BACKEND_BASE_URL = os.getenv("FAGENT_BACKEND_URL", "http://localhost:8000")


class BackendClient:
    """Async HTTP client for the backend API."""

    def __init__(
        self,
        base_url: str = None,
        transport: httpx.AsyncBaseTransport = None,
    ):
        self.base_url = (base_url or BACKEND_BASE_URL).rstrip("/")
        self._client_kwargs = {"transport": transport} if transport else {}

    async def _raise_for_status(self, resp: httpx.Response) -> None:
        """Raise a readable backend error, preserving JSON detail when present."""
        if not resp.is_error:
            return

        detail = None
        try:
            data = resp.json()
            if isinstance(data, dict):
                detail = data.get("detail") or data.get("error")
        except ValueError:
            detail = resp.text.strip() or None

        message = f"Backend returned {resp.status_code}"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message)

    async def create_session(self, title: str = None) -> int:
        """Create a session via backend. Returns integer cid."""
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            payload = {}
            if title:
                payload["title"] = title
            resp = await client.post(
                f"{self.base_url}/api/chat/session/create",
                json=payload if payload else None,
                timeout=10.0,
            )
            await self._raise_for_status(resp)
            return resp.json()["cid"]

    async def send_stream(
        self,
        cid: int,
        message: str,
        model: str = None,
        history_limit: int = None,
    ) -> AsyncGenerator[str, None]:
        """Send message and yield SSE content chunks."""
        payload = {
            "cid": cid,
            "user_message": message,
        }
        if model:
            payload["model"] = model
        if history_limit:
            payload["history_limit"] = history_limit

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat/send/stream",
                json=payload,
                timeout=120.0,
            ) as resp:
                await self._raise_for_status(resp)
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "content" in data:
                                yield data["content"]
                            elif "error" in data:
                                raise RuntimeError(data["error"])
                        except json.JSONDecodeError:
                            pass

    async def send_non_stream(
        self,
        cid: int,
        message: str,
        model: str = None,
        history_limit: int = None,
    ) -> str:
        """Send message and return full response text."""
        payload = {
            "cid": cid,
            "user_message": message,
        }
        if model:
            payload["model"] = model
        if history_limit:
            payload["history_limit"] = history_limit

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat/send",
                json=payload,
                timeout=120.0,
            )
            await self._raise_for_status(resp)
            return resp.json()["content"]

    async def health_check(self) -> bool:
        """Check if backend is available."""
        try:
            async with httpx.AsyncClient(**self._client_kwargs) as client:
                resp = await client.get(
                    f"{self.base_url}/health", timeout=5.0
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def get_models(self) -> list:
        """Get available model list from backend."""
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            resp = await client.get(
                f"{self.base_url}/api/chat/models", timeout=10.0
            )
            await self._raise_for_status(resp)
            return resp.json()
