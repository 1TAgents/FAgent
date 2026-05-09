from backend.services.session_access import can_access_session
from backend.services.storage import MessageStorage


def test_can_access_session_requires_owner_for_user_session():
    session = {"cid": 1, "user_id": 42}

    assert can_access_session(session, {"id": 42})
    assert not can_access_session(session, {"id": 7})
    assert not can_access_session(session, None)


def test_can_access_session_keeps_anonymous_sessions_anonymous():
    session = {"cid": 1, "user_id": None}

    assert can_access_session(session, None)
    assert not can_access_session(session, {"id": 42})
    assert not can_access_session(None, None)


def test_list_conversations_can_filter_anonymous_sessions(tmp_path):
    storage = MessageStorage(db_path=str(tmp_path / "conversations.db"))
    anonymous_cid = storage.create_conversation(title="anonymous")
    user_id = storage.create_user(
        username="owner",
        email="owner@example.com",
        password_hash="hash",
    )
    owned_cid = storage.create_conversation(title="owned", user_id=user_id)

    anonymous = storage.list_conversations(anonymous_only=True)
    owned = storage.list_conversations(user_id=user_id)

    assert [item["cid"] for item in anonymous] == [anonymous_cid]
    assert [item["cid"] for item in owned] == [owned_cid]
