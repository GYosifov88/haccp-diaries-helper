from haccp.config import get_users
from haccp.graph.graph import resolve_user


def test_resolve_user_uses_telegram_display_name_if_present(monkeypatch) -> None:
    monkeypatch.setattr("haccp.graph.graph.get_users", lambda: {"123": "Mapped User"})

    state = {
        "telegram_user_id": "123",
        "chat_id": "123",
        "telegram_user_name": "Иван Петров",
    }
    updated = resolve_user(state)

    assert updated["user"].signature == "Иван Петров"
    assert updated["user"].name == "Mapped User"


def test_resolve_user_uses_display_name_when_no_mapped_user(monkeypatch) -> None:
    monkeypatch.setattr("haccp.graph.graph.get_users", lambda: {})

    state = {
        "telegram_user_id": "123",
        "chat_id": "123",
        "telegram_user_name": "Иван Петров",
    }
    updated = resolve_user(state)

    assert updated["user"].signature == "Иван Петров"
    assert updated["user"].name == "Иван Петров"


def test_resolve_user_falls_back_to_configured_name() -> None:
    state = {
        "telegram_user_id": "123",
        "chat_id": "123",
    }
    updated = resolve_user(state)

    assert updated["user"].signature == "Unknown"
    assert updated["user"].name == "Unknown"
