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
    assert updated["access_denied"] is False
    assert updated["user"].allowed is True


def test_resolve_user_denies_unmapped_user(monkeypatch) -> None:
    monkeypatch.setattr("haccp.graph.graph.get_users", lambda: {})

    state = {
        "telegram_user_id": "123",
        "chat_id": "123",
        "telegram_user_name": "Иван Петров",
    }
    updated = resolve_user(state)

    assert updated["access_denied"] is True
    assert updated["user"].allowed is False
    assert updated["user"].signature == "Иван Петров"


def test_resolve_user_falls_back_to_configured_name(monkeypatch) -> None:
    monkeypatch.setattr("haccp.graph.graph.get_users", lambda: {"123": "Mapped User"})

    state = {
        "telegram_user_id": "123",
        "chat_id": "123",
    }
    updated = resolve_user(state)

    assert updated["user"].signature == "Mapped User"
    assert updated["user"].name == "Mapped User"
    assert updated["user"].allowed is True
    assert updated["access_denied"] is False


def test_resolve_user_unknown_signature_when_unmapped_and_unnamed(monkeypatch) -> None:
    monkeypatch.setattr("haccp.graph.graph.get_users", lambda: {})

    state = {
        "telegram_user_id": "123",
        "chat_id": "123",
    }
    updated = resolve_user(state)

    assert updated["user"].signature == "Unknown"
    assert updated["access_denied"] is True
