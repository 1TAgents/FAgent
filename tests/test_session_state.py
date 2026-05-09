"""
Session State Machine 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.core.session_state import SessionState, SessionStateManager


@pytest.fixture
def manager():
    return SessionStateManager()


class TestSessionStateManager:
    def test_initial_state_is_idle(self, manager):
        assert manager.get_state(1) == SessionState.IDLE

    def test_start_transitions_to_running(self, manager):
        manager.start(1)
        assert manager.get_state(1) == SessionState.RUNNING
        assert manager.is_running(1)

    def test_finish(self, manager):
        manager.start(1)
        manager.finish(1)
        assert manager.get_state(1) == SessionState.FINISHED

    def test_cancel(self, manager):
        manager.start(1)
        assert manager.cancel(1) is True
        assert manager.is_cancelled(1)

    def test_cancel_idle_returns_false(self, manager):
        assert manager.cancel(999) is False

    def test_set_error(self, manager):
        manager.start(1)
        manager.set_error(1)
        assert manager.get_state(1) == SessionState.ERROR

    def test_wait_and_resume(self, manager):
        manager.start(1)
        manager.wait(1)
        assert manager.get_state(1) == SessionState.WAITING
        # 模拟外部确认后恢复
        manager.start(1)
        assert manager.is_running(1)

    def test_is_active(self, manager):
        manager.start(1)
        assert manager.get_info(1)["is_active"] is True
        manager.finish(1)
        assert manager.get_info(1)["is_active"] is False

    def test_is_terminal(self, manager):
        for state_action in [
            (SessionState.FINISHED, manager.finish),
            (SessionState.ERROR, manager.set_error),
            (SessionState.CANCELLED, manager.cancel),
        ]:
            manager.start(1)
            state_action[1](1)
            assert manager.get_info(1)["is_terminal"] is True
            manager.reset(1)

    def test_list_active(self, manager):
        manager.start(1)
        manager.start(2)
        active = manager.list_active()
        assert len(active) == 2
        manager.finish(1)
        assert len(manager.list_active()) == 1

    def test_nonexistent_session_returns_idle(self, manager):
        assert manager.get_state(9999) == SessionState.IDLE

    def test_get_info_returns_none_for_unknown(self, manager):
        # Don't call get_or_create, just check raw
        assert manager.get_info(9999) is None
