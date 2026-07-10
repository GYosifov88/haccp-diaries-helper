from haccp.graph.nodes.pending import continue_pending_entry
from haccp.models.state import ExtractedEntry


def test_continue_pending_entry_merges_follow_up() -> None:
    base_entry = ExtractedEntry(entry_type="incoming_goods", supplier="Стар", signature="Иван")
    updated = continue_pending_entry(base_entry, "добави срок на годност 10.07.2026")

    assert updated.expiry_date == "10.07.2026"
