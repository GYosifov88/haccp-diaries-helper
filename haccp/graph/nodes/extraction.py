from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from langchain_openai import ChatOpenAI

from haccp.config import get_diaries, get_settings
from haccp.models.state import ExtractedEntry, InvoiceItem
from haccp.services.media import OCRService, TranscriptionService


def _get_diary_schema(entry_type: str) -> dict[str, Any] | None:
    diaries = get_diaries()
    diary = diaries.get(entry_type)
    if diary is None:
        return None
    return {
        "required_fields": diary.required_fields,
        "columns": diary.columns,
        "supports_invoice_items": diary.supports_invoice_items,
    }


def build_extraction_prompt(entry_type: str, raw_text: str, signature: str | None = None) -> str:
    """Create a deterministic prompt mirroring the structure used by the n8n workflow."""
    signature_value = signature or "неизвестен"
    diary_schema = _get_diary_schema(entry_type)
    required_fields = diary_schema.get("required_fields", []) if diary_schema else []
    field_list = ", ".join(required_fields) if required_fields else "the fields implied by the diary"

    schema_hint = ""
    if diary_schema:
        schema_hint = (
            f"Schema fields for {entry_type}: {field_list}.\n"
            f"Use the diary-specific fields that best match the text.\n"
        )
        if diary_schema.get("supports_invoice_items"):
            schema_hint += "If the text contains multiple products, return them in an items array.\n"

    allowed_types = [
        "temperature_fridge", "temperature_thermal", "incoming_goods", "cleaning", "personal_hygiene",
        "waste", "pest_control", "equipment_control", "water_control", "ddd", "traceability", "complaints"
    ]
    return (
        f"You are an AI assistant for HACCP food safety documentation.\n"
        f"The user input is in Bulgarian.\n"
        f"Extract a structured {entry_type} diary entry from the following text.\n"
        f"{schema_hint}"
        f"If the diary type is not already selected, infer the correct entry_type from the text.\n"
        f"Use one of these exact entry_type values only: {', '.join(allowed_types)}.\n"
        f"The signature field must always be: {signature_value}.\n"
        f"If a value is unknown, use 'неизвестна'.\n"
        f"Return ONLY valid JSON inside a single 'output' object.\n"
        f"Do not use markdown code fences. Do not escape JSON.\n"
        f"User input:\n{raw_text}"
    )


_DATE_PATTERN = re.compile(r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})")
_TEMPERATURE_PATTERN = re.compile(r"(-?\d+(?:[.,]\d+)?)")
_FRIDGE_PATTERN = re.compile(r"(хладилник|fridge)\s*(?:№|#)?\s*(\d+)", re.IGNORECASE)
_FRIDGE_TEMPERATURE_PATTERN = re.compile(
    r"(?:хладилник|fridge)\s*(?:№|#)?\s*(\d+)\D+?([+-]?\d+(?:[.,]\d*)?)",
    re.IGNORECASE,
)
_PERSONAL_HYGIENE_EMPLOYEE_PATTERN = re.compile(
    r"^(?P<employee>[А-Я][а-я]+)\b.*?(?:започна работа|е на смяна|работи)",
    re.IGNORECASE,
)

_WASTE_QUANTITY_PATTERN = re.compile(
    r"(?:изхвърлени|изхвърлен|изхвърли|прибран|събрани?)\s*(?P<quantity>[0-9]+)\s*(?P<unit>чувала|бр|бр\.|кг|килограма|л)?(?:\s+[^,.;:\n]+)?\s+(?:боклук|отпадък)",
    re.IGNORECASE,
)
_WASTE_CONTAINER_PATTERN = re.compile(
    r"в\s*(?P<container>(?:контейнерите|контейнера|кошовете|кофа|контейнер)\s*(?:за\s*)?[^.\n]+)",
    re.IGNORECASE,
)
_WASTE_DISPOSED_WHERE_PATTERN = re.compile(
    r"(?:в|във|до|към)\s*(?P<disposed_where>контейнерите|контейнера|кофите|кофата|местото|площада|квартала|пътя|улицата)[^.\n]*",
    re.IGNORECASE,
)


def _extract_personal_hygiene_employee(text: str) -> str | None:
    match = _PERSONAL_HYGIENE_EMPLOYEE_PATTERN.search(text)
    if match:
        return match.group("employee")
    return None


def _extract_personal_hygiene_bool(text: str, patterns: list[str]) -> str:
    normalized = text.lower()
    return "да" if any(p in normalized for p in patterns) else "не"


def _extract_waste_quantity(text: str) -> tuple[str | None, str | None]:
    match = _WASTE_QUANTITY_PATTERN.search(text)
    if not match:
        return None, None

    quantity = match.group("quantity")
    unit = match.group("unit") or "бр"
    normalized_units = {
        "чувала": "бр",
        "чувал": "бр",
        "бр": "бр",
        "бр.": "бр",
        "кг": "кг",
        "килограма": "кг",
        "л": "л",
    }
    unit = normalized_units.get(unit.lower(), unit)
    return quantity, unit


def _extract_waste_container(text: str) -> str | None:
    match = _WASTE_CONTAINER_PATTERN.search(text)
    if match:
        return match.group("container").strip()
    return None


def _extract_waste_disposed_where(text: str) -> str | None:
    match = _WASTE_DISPOSED_WHERE_PATTERN.search(text)
    if match:
        return match.group("disposed_where").strip()
    return None


def _today() -> str:
    return datetime.now().strftime("%d.%m.%Y")


def _now_time() -> str:
    return datetime.now().strftime("%H:%M")


def _extract_date(text: str) -> str | None:
    match = _DATE_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def _extract_temperature(text: str) -> str | None:
    matches = _TEMPERATURE_PATTERN.findall(text)
    if not matches:
        return None
    value = matches[0].replace(",", ".")
    return value


def parse_llm_json_response(response_text: str) -> dict[str, Any] | None:
    """Parse structured JSON from a model response that may be wrapped in markdown code fences."""
    candidate = response_text.strip()
    if not candidate:
        return None

    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def apply_diary_specific_mapping(entry: ExtractedEntry, payload: dict[str, Any]) -> ExtractedEntry:
    """Map a parsed LLM payload into the appropriate diary fields for the selected entry type."""
    entry_type = str(payload.get("entry_type") or entry.entry_type)
    entry.entry_type = entry_type  # type: ignore[assignment]

    field_aliases = {
        "temperature_fridge": {
            "fridge_number": ["fridge_number", "fridge", "fridge_no"],
            "temperature": ["temperature", "temp"],
            "corrective_action": ["corrective_action", "action"],
        },
        "temperature_thermal": {
            "product": ["product", "item"],
            "batch": ["batch", "lot"],
            "core_temperature": ["core_temperature", "temperature"],
            "operator": ["operator", "executor"],
        },
        "incoming_goods": {
            "supplier": ["supplier", "vendor"],
            "product": ["product", "item_name"],
            "temperature": ["temperature", "temp"],
            "expiry_date": ["expiry_date", "expiry"],
            "package_condition": ["package_condition", "packaging"],
            "documents": ["documents", "invoice_number"],
            "decision": ["decision", "result"],
            "quantity": ["quantity", "qty"],
            "unit": ["unit", "measure"],
            "note": ["note", "remarks"],
        },
        "cleaning": {
            "area": ["area", "zone"],
            "cleaning_type": ["cleaning_type", "type"],
            "chemical": ["chemical", "product"],
            "frequency": ["frequency", "interval"],
            "executor": ["executor", "performed_by"],
        },
        "personal_hygiene": {
            "employee": ["employee", "person"],
            "clean_uniform": ["clean_uniform", "uniform"],
            "washed_hands": ["washed_hands", "hands"],
            "no_jewelry": ["no_jewelry", "jewelry"],
        },
        "waste": {
            "waste_type": ["waste_type", "type"],
            "quantity": ["quantity", "qty"],
            "container": ["container", "bin"],
            "disposed_where": ["disposed_where", "location"],
            "executor": ["executor", "performed_by"],
        },
        "pest_control": {
            "zone": ["zone", "area"],
            "observation": ["observation", "signs"],
            "action": ["action", "measure"],
            "executor": ["executor", "performed_by"],
        },
        "equipment_control": {
            "equipment": ["equipment", "device"],
            "status": ["status", "condition"],
            "note": ["note", "remarks"],
            "corrective_action": ["corrective_action", "action"],
            "executor": ["executor", "performed_by"],
        },
        "water_control": {
            "source": ["source", "water_source"],
            "certificate": ["certificate", "cert"],
            "note": ["note", "remarks"],
        },
        "ddd": {
            "treatment_type": ["treatment_type", "type"],
            "executor": ["executor", "company"],
            "chemical": ["chemical", "product"],
            "zone": ["zone", "area"],
            "protocol_number": ["protocol_number", "protocol"],
        },
        "traceability": {
            "product": ["product", "item"],
            "batch": ["batch", "lot"],
            "supplier": ["supplier", "vendor"],
            "quantity": ["quantity", "qty"],
            "used_in": ["used_in", "dish"],
        },
        "complaints": {
            "client": ["client", "customer"],
            "description": ["description", "details"],
            "product": ["product", "item"],
            "action": ["action", "measure"],
            "result": ["result", "outcome"],
        },
    }

    aliases = field_aliases.get(entry_type, {})
    for field_name, aliases_for_field in aliases.items():
        for alias in aliases_for_field:
            if alias in payload and payload[alias] is not None:
                setattr(entry, field_name, payload[alias])
                break

    if entry.entry_type == "incoming_goods":
        items_payload = payload.get("items") or payload.get("invoice_items")
        if isinstance(items_payload, list):
            parsed_items: list[InvoiceItem] = []
            for item_payload in items_payload:
                if not isinstance(item_payload, dict):
                    continue

                item_product = (
                    item_payload.get("product")
                    or item_payload.get("item")
                    or item_payload.get("name")
                    or item_payload.get("item_name")
                    or "неизвестен продукт"
                )
                item_quantity = (
                    item_payload.get("quantity")
                    or item_payload.get("qty")
                    or 1
                )
                item_unit = (
                    item_payload.get("unit")
                    or item_payload.get("measure")
                    or "бр"
                )
                item_temperature = (
                    item_payload.get("temperature")
                    or item_payload.get("temp")
                    or "неизвестна"
                )
                item_expiry = (
                    item_payload.get("expiry_date")
                    or item_payload.get("expiry")
                    or "неизвестна"
                )
                item_package = (
                    item_payload.get("package_condition")
                    or item_payload.get("packaging")
                    or "неизвестна"
                )
                item_decision = (
                    item_payload.get("decision")
                    or item_payload.get("result")
                    or "прието"
                )
                parsed_items.append(
                    InvoiceItem(
                        product=item_product,
                        quantity=item_quantity,
                        unit=item_unit,
                        temperature=item_temperature,
                        expiry_date=item_expiry,
                        package_condition=item_package,
                        decision=item_decision,
                    )
                )

            if parsed_items:
                entry.items = parsed_items
                first_item = parsed_items[0]
                entry.product = entry.product or first_item.product
                entry.quantity = entry.quantity or first_item.quantity
                entry.unit = entry.unit or first_item.unit
                entry.temperature = entry.temperature or first_item.temperature
                entry.expiry_date = entry.expiry_date or first_item.expiry_date
                entry.package_condition = entry.package_condition or first_item.package_condition
                entry.decision = entry.decision or first_item.decision

    if entry.entry_type == "incoming_goods" and entry.product and entry.supplier:
        entry.note = entry.note or "Автоматично извлечено от текста"

    return entry


def _build_entry(entry_type: str, *, text: str, signature: str | None = None) -> ExtractedEntry:
    entry = ExtractedEntry(entry_type=entry_type, signature=signature or "неизвестен", date=_today(), time=_now_time())

    if entry_type == "temperature_fridge":
        fridge_temp_match = _FRIDGE_TEMPERATURE_PATTERN.search(text)
        if fridge_temp_match:
            entry.fridge_number = fridge_temp_match.group(1)
            entry.temperature = fridge_temp_match.group(2).replace(",", ".")
        else:
            fridge_match = _FRIDGE_PATTERN.search(text)
            if fridge_match:
                entry.fridge_number = fridge_match.group(2)
                temp_match = _extract_temperature(text[fridge_match.end():])
            else:
                temp_match = _extract_temperature(text)
            if not temp_match:
                temp_match = _extract_temperature(text)
            if temp_match:
                entry.temperature = temp_match
        if entry.temperature is not None and float(str(entry.temperature).replace(",", ".")) > 4:
            entry.corrective_action = "Проверка и регулиране на температурата"

    if entry_type == "incoming_goods":
        entry.supplier = "неизвестна"
        if "доставчик" in text.lower():
            entry.supplier = "извлечено от текста"
        entry.documents = "неизвестна"
        entry.product = "неизвестен продукт"
        entry.quantity = 1
        entry.unit = "бр"
        entry.temperature = "неизвестна"
        entry.expiry_date = "неизвестна"
        entry.package_condition = "неизвестна"
        entry.decision = "прието"

    if entry_type == "cleaning":
        entry.area = "неизвестна"
        entry.cleaning_type = "неизвестна"
        entry.chemical = "неизвестна"
        entry.frequency = "неизвестна"

    if entry_type == "personal_hygiene":
        entry.employee = _extract_personal_hygiene_employee(text) or "неизвестен"
        entry.clean_uniform = _extract_personal_hygiene_bool(
            text,
            ["чисто облекло", "чиста униформа", "с чисто облекло", "чисто облекло"],
        )
        entry.washed_hands = _extract_personal_hygiene_bool(
            text,
            ["измити ръце", "изми ръцете", "изми ръце", "измити ръце"],
        )
        entry.no_jewelry = _extract_personal_hygiene_bool(
            text,
            ["без бижута", "без бижу", "без украшения"],
        )

    if entry_type == "waste":
        entry.waste_type = "боклук"
        quantity, unit = _extract_waste_quantity(text)
        entry.quantity = f"{quantity} {unit}" if quantity else None
        entry.container = _extract_waste_container(text) or "контейнери за битов отпадък"
        entry.disposed_where = _extract_waste_disposed_where(text) or "контейнерите за битов отпадък"

    if entry_type == "temperature_thermal":
        entry.product = "неизвестен продукт"
        entry.batch = "неизвестна"
        entry.core_temperature = "неизвестна"
        entry.operator = "неизвестен"

    return entry


def _invoke_llm_extraction(prompt: str, *, entry_type: str) -> dict[str, Any] | None:
    settings = get_settings()
    llm = ChatOpenAI(model=settings.openai_model, temperature=0)
    response = llm.invoke(prompt)
    parsed = parse_llm_json_response(str(response.content))
    if parsed and isinstance(parsed, dict):
        return parsed
    return None


def extract_entry(state: dict[str, Any]) -> dict[str, Any]:
    """Create a structured diary entry from the current payload."""
    raw_text = state.get("raw_text") or ""
    input_kind = state.get("input_kind") or "text"
    file_bytes = state.get("file_bytes")
    file_mime = state.get("file_mime") or "image/jpeg"

    if input_kind in {"photo", "document"} and file_bytes:
        try:
            raw_text = OCRService().extract_text(file_bytes, file_mime)
        except Exception:
            raw_text = raw_text or ""

    if input_kind == "voice" and file_bytes:
        try:
            raw_text = TranscriptionService().transcribe(file_bytes, filename=(state.get("file_mime") or file_mime))
        except Exception:
            raw_text = raw_text or ""

    if not raw_text and state.get("input_text"):
        raw_text = state["input_text"]

    entry_type = state.get("entry_type") or "unknown"
    if entry_type == "unknown":
        from haccp.graph.nodes.classification import classify_entry_type

        entry_type = classify_entry_type(raw_text)

    signature = None
    user = state.get("user")
    if user is not None:
        signature = user.signature

    prompt = build_extraction_prompt(entry_type, raw_text, signature)
    state["input_text"] = prompt

    llm_payload = None
    try:
        llm_payload = _invoke_llm_extraction(prompt, entry_type=entry_type)
    except Exception:
        llm_payload = None

    entry = _build_entry(entry_type, text=raw_text, signature=signature)
    pending = state.get("pending_entry")
    if pending is not None and isinstance(pending, ExtractedEntry):
        from haccp.graph.nodes.pending import merge_pending_entry

        entry = merge_pending_entry(entry, pending.model_dump(exclude_none=True, exclude={"entry_type"}))
    if llm_payload and isinstance(llm_payload.get("output"), dict):
        output = llm_payload["output"]
        if isinstance(output, dict):
            entry_type = str(output.get("entry_type") or entry_type)
            entry = apply_diary_specific_mapping(entry, output)
            entry.entry_type = entry_type  # type: ignore[assignment]

    entry.date = _extract_date(raw_text) or entry.date
    if entry_type == "temperature_fridge" and entry.temperature is None:
        entry.temperature = "неизвестна"

    # Try to extract expiry_date from the raw text for incoming goods
    if entry_type == "incoming_goods":
        if not entry.expiry_date or entry.expiry_date == "неизвестна":
            expiry = _extract_date(raw_text)
            if expiry:
                entry.expiry_date = expiry

    state["extracted"] = entry
    state["entry_type"] = entry_type
    return state
