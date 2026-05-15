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

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or BACKEND_BASE_URL).rstrip("/")

    async def create_session(self, title: str = None) -> int:
        """Create a session via backend. Returns integer cid."""
        async with httpx.AsyncClient() as client:
            payload = {}
            if title:
                payload["title"] = title
            resp = await client.post(
                f"{self.base_url}/api/chat/session/create",
                json=payload if payload else None,
                timeout=10.0,
            )
            resp.raise_for_status()
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

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat/send/stream",
                json=payload,
                timeout=120.0,
            ) as resp:
                resp.raise_for_status()
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

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/chat/send",
                json=payload,
                timeout=120.0,
            )
            resp.raise_for_status()
            return resp.json()["content"]

    async def health_check(self) -> bool:
        """Check if backend is available."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/health", timeout=5.0
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def get_models(self) -> list:
        """Get available model list from backend."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/chat/models", timeout=10.0
            )
            resp.raise_for_status()
            return resp.json()
