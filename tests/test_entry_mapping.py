from haccp.graph.nodes.extraction import apply_diary_specific_mapping
from haccp.models.state import ExtractedEntry


def test_apply_diary_specific_mapping_sets_expected_fields() -> None:
    entry = ExtractedEntry(entry_type="incoming_goods", signature="Иван")
    payload = {"entry_type": "incoming_goods", "supplier": "Тестов доставчик", "product": "мляко", "temperature": "3", "expiry_date": "10.07.2026", "package_condition": "добра", "documents": "Ф123", "decision": "прието"}

    mapped = apply_diary_specific_mapping(entry, payload)

    assert mapped.supplier == "Тестов доставчик"
    assert mapped.product == "мляко"
    assert mapped.decision == "прието"
    assert mapped.entry_type == "incoming_goods"
