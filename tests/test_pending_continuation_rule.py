from __future__ import annotations

import pytest

from haccp.graph.nodes.pending import is_pending_continuation
from haccp.models.state import ExtractedEntry
from haccp.services.pending_store import PendingEntry


def _pending(entry_type: str) -> PendingEntry:
    return PendingEntry(
        chat_id="1",
        entry_type=entry_type,
        entry_id="pending",
        sheet_name="pending",
        row_number=0,
        missing=[],
        asked_at=0.0,
        entry=ExtractedEntry(entry_type=entry_type),
    )


@pytest.mark.parametrize(
    "pending_type, missing, text, new_type, expected",
    [
        # reply that supplies a missing field
        ("incoming_goods", ["expiry_date"], "срок на годност 10.07.2026", "incoming_goods", True),
        # bare replies that classify as unknown
        ("incoming_goods", ["expiry_date"], "10.07.2026", "unknown", True),
        ("incoming_goods", ["supplier"], "Метро", "unknown", True),
        # answers the missing field even though it classifies as another type
        ("temperature_thermal", ["core_temperature"], "ядрена температура 75", "temperature_fridge", True),
        # clearly different type: re-states a filled required field
        ("incoming_goods", ["expiry_date"], "Хладилник 2 температура 3 градуса", "temperature_fridge", False),
        # clearly different type: no labelled fields at all
        ("incoming_goods", ["expiry_date"], "Почистване на кухнята с белина", "cleaning", False),
        # same type, complete, re-stating a filled required field
        ("incoming_goods", ["expiry_date"], "Доставка от Билла, доставчик Билла, продукт мляко", "incoming_goods", False),
        # same-type keywords but no field answered
        ("incoming_goods", ["expiry_date"], "Нова доставка от Билла", "incoming_goods", False),
        # pending type without a diary config
        ("unknown", ["supplier"], "срок на годност 10.07.2026", "unknown", False),
    ],
)
def test_is_pending_continuation(offline, pending_type, missing, text, new_type, expected) -> None:
    assert is_pending_continuation(_pending(pending_type), missing, text, new_type) is expected
