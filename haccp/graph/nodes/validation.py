from __future__ import annotations

from typing import Any

from haccp.config import get_diaries
from haccp.models.state import ExtractedEntry


def validate_entry(state: dict[str, Any]) -> dict[str, Any]:
    """Ensure the extracted entry has the required fields for its diary type."""
    entry = state.get("extracted")
    if not isinstance(entry, ExtractedEntry):
        state["validation_errors"] = ["No extracted entry was created."]
        return state

    diaries = get_diaries()
    diary = diaries.get(entry.entry_type)
    if diary is None:
        state["validation_errors"] = [f"Unsupported entry type: {entry.entry_type}"]
        return state

    missing_fields: list[str] = []
    for field in diary.required_fields:
        value = getattr(entry, field, None)
        if value is None or str(value).strip().lower() in {"", "неизвестна", "неизвестен", "unknown", "n/a"}:
            missing_fields.append(field)

    if entry.entry_type == "incoming_goods" and entry.product and entry.supplier:
        entry.note = entry.note or "Автоматично извлечено от входящия текст"

    state["validation_errors"] = missing_fields
    state["extracted"] = entry
    return state
