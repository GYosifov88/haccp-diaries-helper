from haccp.bot import build_payload


def test_build_payload_from_text_message() -> None:
    payload = build_payload(
        user_id="123",
        chat_id="123",
        user_name="Иван Петров",
        text="купихме стоки",
    )

    assert payload["telegram_user_id"] == "123"
    assert payload["telegram_user_name"] == "Иван Петров"
    assert payload["raw_text"] == "купихме стоки"
    assert payload["input_kind"] == "text"
