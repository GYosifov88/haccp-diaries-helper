from haccp.graph.nodes.extraction import apply_diary_specific_mapping
from haccp.models.state import ExtractedEntry


def test_apply_diary_specific_mapping_parses_items_array() -> None:
    entry = ExtractedEntry(entry_type="incoming_goods", signature="Иван")
    payload = {
        "entry_type": "incoming_goods",
        "supplier": "Тестов доставчик",
        "items": [
            {
                "product": "мляко",
                "quantity": 10,
                "unit": "л",
                "temperature": "3",
                "expiry_date": "10.07.2026",
                "package_condition": "добра",
                "decision": "прието",
            },
            {
                "product": "хляб",
                "quantity": 5,
                "unit": "бр",
                "temperature": "неизвестна",
                "expiry_date": "15.08.2026",
                "package_condition": "добра",
                "decision": "прието",
            },
        ],
    }

    mapped = apply_diary_specific_mapping(entry, payload)

    assert mapped.entry_type == "incoming_goods"
    assert mapped.product == "мляко"
    assert mapped.quantity == 10
    assert mapped.unit == "л"
    assert mapped.expiry_date == "10.07.2026"
    assert mapped.items is not None
    assert len(mapped.items) == 2
    assert mapped.items[1].product == "хляб"
