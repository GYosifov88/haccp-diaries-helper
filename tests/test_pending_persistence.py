from haccp.graph.nodes.pending import save_pending_entry, load_pending_entry
from haccp.models.state import ExtractedEntry


def test_pending_entry_round_trip(tmp_path) -> None:
    entry = ExtractedEntry(entry_type="incoming_goods", supplier="Тест", signature="Иван")
    db_path = tmp_path / "pending.db"

    saved = save_pending_entry(entry, missing_fields=["expiry_date"], chat_id="42", db_path=str(db_path))
    loaded = load_pending_entry(chat_id="42", db_path=str(db_path))

    assert saved is True
    assert loaded is not None
    assert loaded.entry_type == "incoming_goods"
    assert loaded.missing[0].field == "expiry_date"
