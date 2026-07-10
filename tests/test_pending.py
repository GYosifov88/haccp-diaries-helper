from haccp.graph.nodes.pending import handle_pending
from haccp.models.state import ExtractedEntry


def test_handle_pending_sets_follow_up_when_fields_missing(tmp_path) -> None:
    state = {
        "chat_id": "123",
        "extracted": ExtractedEntry(entry_type="incoming_goods", signature="Иван"),
        "validation_errors": ["supplier", "product"],
        "reply_messages": [],
        "pending_handled": False,
    }

    updated = handle_pending(state, db_path=str(tmp_path / "pending.db"))

    assert updated["pending_handled"] is True
    assert any("липсва" in message.lower() for message in updated["reply_messages"])
