from haccp.graph.nodes.response import build_response_message
from haccp.models.state import ExtractedEntry


def test_build_response_message_includes_summary_and_missing_fields() -> None:
    entry = ExtractedEntry(entry_type="incoming_goods", supplier="Тестов доставчик", product="мляко", signature="Иван")
    message = build_response_message(entry, missing_fields=["expiry_date"], written=True)

    assert "incoming_goods" in message
    assert "Тестов доставчик" in message
    assert "expiry_date" in message
    assert "записан" in message
