from __future__ import annotations

from haccp.models.state import ExtractedEntry


def build_response_message(entry: ExtractedEntry, *, missing_fields: list[str] | None = None, written: bool) -> str:
    """Build a human-friendly confirmation message for a processed diary entry."""
    missing_fields = missing_fields or []
    summary_parts: list[str] = [f"Тип: {entry.entry_type}"]

    if entry.entry_type == "incoming_goods":
        if entry.supplier:
            summary_parts.append(f"Доставчик: {entry.supplier}")
        if entry.product:
            summary_parts.append(f"Продукт: {entry.product}")
        if entry.decision:
            summary_parts.append(f"Решение: {entry.decision}")
    elif entry.entry_type == "temperature_fridge":
        if entry.fridge_number:
            summary_parts.append(f"Хладилник: {entry.fridge_number}")
        if entry.temperature is not None:
            summary_parts.append(f"Температура: {entry.temperature}")
    elif entry.entry_type == "temperature_thermal":
        if entry.product:
            summary_parts.append(f"Продукт: {entry.product}")
        if entry.core_temperature is not None:
            summary_parts.append(f"Ядро: {entry.core_temperature}")

    if missing_fields:
        summary_parts.append(f"Липсващи полета: {', '.join(missing_fields)}")

    status = "записан" if written else "подготвен"
    return f"Записът е {status}. " + " | ".join(summary_parts)
