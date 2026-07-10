from haccp.bot import handle_message


def test_handle_message_returns_follow_up_for_pending_entry(monkeypatch) -> None:
    def fake_run_workflow(payload):
        return {"reply_messages": ["Имате незавършен запис за incoming_goods. Моля, попълнете следните полета: supplier."], "finished": True}

    monkeypatch.setattr("haccp.bot.run_workflow", fake_run_workflow)
    result = handle_message(user_id="1", chat_id="1", text="hello")

    assert result["reply_messages"][0].startswith("Имате незавършен запис")
