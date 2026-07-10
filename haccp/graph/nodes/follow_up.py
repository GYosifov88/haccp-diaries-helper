from __future__ import annotations


def build_follow_up_message(entry_type: str, missing_fields: list[str]) -> str:
    """Build a concise follow-up prompt for a diary entry with missing required fields."""
    field_list = ", ".join(missing_fields)
    return (
        f"Имате незавършен запис за {entry_type}. "
        f"Моля, попълнете следните полета: {field_list}."
    )
