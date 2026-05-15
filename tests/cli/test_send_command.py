from click.testing import CliRunner

from src.cli.commands import send as send_module


class UnhealthyBackend:
    base_url = "http://localhost:8000"

    async def health_check(self):
        return False


class DummyMemory:
    current_cid = None

    def save_message(self, **kwargs):
        return "msg_1"


def test_send_unhealthy_backend_hint_is_portable(monkeypatch):
    monkeypatch.setattr(send_module, "get_backend_client", lambda: UnhealthyBackend())
    monkeypatch.setattr(send_module, "get_memory", lambda: DummyMemory())

    result = CliRunner().invoke(send_module.send, ["你好"])

    assert result.exit_code == 1
    assert "FAGENT_BACKEND_URL" in result.output
    assert ("/" + "Users/") not in result.output


def test_send_non_stream_request_failure_exits_nonzero(monkeypatch):
    class FailingBackend:
        base_url = "http://localhost:8000"

        async def health_check(self):
            return True

        async def create_session(self, title=None):
            return 1

        async def send_non_stream(self, **kwargs):
            raise RuntimeError("backend failed")

    memory = DummyMemory()
    monkeypatch.setattr(send_module, "get_backend_client", lambda: FailingBackend())
    monkeypatch.setattr(send_module, "get_memory", lambda: memory)

    result = CliRunner().invoke(send_module.send, ["你好", "--no-stream"])

    assert result.exit_code == 1
    assert "请求失败" in result.output
