from haccp.graph.graph import run_workflow


def test_run_workflow_preserves_telegram_user_name_into_signature(offline) -> None:
    offline["users"]["123"] = "Иван Петров"

    result = run_workflow({
        "telegram_user_id": "123",
        "chat_id": "123",
        "telegram_user_name": "Иван Петров",
        "input_kind": "text",
        "raw_text": "купихме стоки",
        "input_text": "купихме стоки",
    })

    assert result["access_denied"] is False
    assert result["user"].signature == "Иван Петров"
    assert result["user"].name == "Иван Петров"
