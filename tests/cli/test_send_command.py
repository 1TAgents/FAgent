from click.testing import CliRunner

from src.cli.commands import send as send_module


class UnhealthyBackend:
    base_url = "http://localhost:8000"

    async def health_check(self):
        return False


class DummyMemory:
    current_cid = None


def test_send_unhealthy_backend_hint_is_portable(monkeypatch):
    monkeypatch.setattr(send_module, "get_backend_client", lambda: UnhealthyBackend())
    monkeypatch.setattr(send_module, "get_memory", lambda: DummyMemory())

    result = CliRunner().invoke(send_module.send, ["你好"])

    assert result.exit_code == 1
    assert "FAGENT_BACKEND_URL" in result.output
    assert ("/" + "Users/") not in result.output
