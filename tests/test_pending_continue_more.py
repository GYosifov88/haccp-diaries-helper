from haccp.graph.nodes.pending import continue_pending_entry
from haccp.models.state import ExtractedEntry


def test_continue_pending_parses_batch() -> None:
    entry = ExtractedEntry(entry_type="incoming_goods")
    updated = continue_pending_entry(entry, "партиен номер ABC123")

    assert getattr(updated, "batch") == "ABC123"


def test_continue_pending_parses_temperature() -> None:
    entry = ExtractedEntry(entry_type="temperature_fridge")
    updated = continue_pending_entry(entry, "температура 4.5°C")

    assert updated.temperature is not None and "4.5" in str(updated.temperature)


def test_continue_pending_parses_product() -> None:
    entry = ExtractedEntry(entry_type="incoming_goods")
    updated = continue_pending_entry(entry, "продукт: Мляко")

    assert updated.product is not None and "Мляко" in updated.product
