from haccp.graph.nodes.pending import merge_pending_entry
from haccp.models.state import ExtractedEntry


def test_merge_pending_entry_updates_existing_fields() -> None:
    entry = ExtractedEntry(entry_type="incoming_goods", supplier="Старо", signature="Иван")
    merged = merge_pending_entry(entry, {"supplier": "Ново", "expiry_date": "10.07.2026"})

    assert merged.supplier == "Ново"
    assert merged.expiry_date == "10.07.2026"
