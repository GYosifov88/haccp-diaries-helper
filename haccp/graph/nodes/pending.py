from __future__ import annotations

import json
import re
import time
from typing import Any

from haccp.models.state import ExtractedEntry, MissingField
from haccp.services.pending_store import PendingEntry, PendingStore
from haccp.config import get_settings, get_diaries

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover - optional dependency in tests
    ChatOpenAI = None


# Simple globals for caching/rate-limiting
_LLM_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_LAST_LLM_CALL: float = 0.0


def save_pending_entry(entry: ExtractedEntry, *, missing_fields: list[str], chat_id: str, db_path: str | None = None) -> bool:
    """Persist a pending entry so a later message can continue filling it in."""
    store = PendingStore(db_path=db_path)
    pending = PendingEntry(
        chat_id=chat_id,
        entry_type=entry.entry_type,
        entry_id="pending",
        sheet_name="pending",
        row_number=0,
        missing=[MissingField(field=field, label=field) for field in missing_fields],
        asked_at=time.time(),
        entry=entry,
    )
    store.save(pending)
    return True


def load_pending_entry(*, chat_id: str, db_path: str | None = None) -> PendingEntry | None:
    store = PendingStore(db_path=db_path)
    return store.get(chat_id)


def clear_pending_entry(*, chat_id: str, db_path: str | None = None) -> None:
    PendingStore(db_path=db_path).clear(chat_id)


def should_continue_pending_entry(text: str | None) -> bool:
    """Return True when a message looks like a follow-up to an existing pending diary entry."""
    if not text:
        return False
    normalized = text.lower().strip()
    return any(keyword in normalized for keyword in ("продължи", "продължавам", "добави", "липсва", "срок", "годност", "допълни", "продължение"))


def parse_follow_up_fields(text: str) -> dict[str, str]:
    """Return the explicitly labelled diary fields found in a follow-up message."""
    normalized = text.strip()
    payload: dict[str, str] = {}
    patterns: list[tuple[str, str]] = [
        ("expiry_date", r"(?:срок\s+на\s+годност|годност|expiry)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})"),
        ("batch", r"(?:партиен(?:\s+номер)?|парти|batch)\s*[:\-]?\s*([^,;\n]+)"),
        ("core_temperature", r"(?:ядрена\s+температура|ядрена)\s*[:\-]?\s*([+-]?\d+[.,]?\d*\s*(?:°?C|C|°|градус)?)"),
        ("temperature", r"(?:температура|temp)\s*[:\-]?\s*([+-]?\d+[.,]?\d*\s*(?:°?C|C|°|градус)?)"),
        ("product", r"(?:продукт(?:а)?|продукта|име)\s*[:\-]?\s*([^,;\n]+)"),
        ("supplier", r"(?:снабдител|доставчик|доставчик:)\s*[:\-]?\s*([^,;\n]+)"),
        ("quantity", r"(?:количество|кол\.|бр\.)\s*[:\-]?\s*([0-9]+(?:[.,][0-9]+)?)"),
        ("unit", r"(?:единица|мерна\s+единица|бр)\s*[:\-]?\s*([^,;\n]+)"),
        ("package_condition", r"(?:състояние|опаковка|състояние\s+на\s+опаковката)\s*[:\-]?\s*([^,;\n]+)"),
        ("documents", r"(?:документ|документи)\s*[:\-]?\s*([^,;\n]+)"),
        ("decision", r"(?:решение|прието|отхвърлено)\s*[:\-]?\s*([^,;\n]+)"),
        ("note", r"(?:бележка|коментар)\s*[:\-]?\s*([^,;\n]+)"),
        ("date", r"(?:дата)\s*[:\-]?\s*([^,;\n]+)"),
        ("time", r"(?:час|време)\s*[:\-]?\s*([^,;\n]+)"),
        ("employee", r"(?:служител|работник|сътрудник)\s*[:\-]?\s*([^,;\n]+)"),
        ("fridge_number", r"(?:хладилник|фризер|фриза|фризер\s+номер)\s*[:\-]?\s*(\d+)")
    ]

    # Attempt to collect all matching fields (don't stop at first match)
    for field, pattern in patterns:
        for match in re.finditer(pattern, normalized, flags=re.IGNORECASE):
            value = match.group(1).strip()
            if value:
                payload[field] = value

    return payload


def is_pending_continuation(pending: PendingEntry | ExtractedEntry, missing: list[str], text: str | None, new_type: str) -> bool:
    """Decide whether a message answers the pending follow-up or starts a new entry.

    ``pending`` only needs an ``entry_type`` (a stored PendingEntry or the pending ExtractedEntry).
    """
    diary = get_diaries().get(pending.entry_type)
    if diary is None:
        return False
    hits = parse_follow_up_fields(text or "")
    # Re-stating a required field the pending entry already has means a fresh entry.
    if any(f in diary.required_fields and f not in missing for f in hits):
        return False
    # Supplying a field we are waiting for is a continuation.
    if any(f in missing for f in hits):
        return True
    # Bare replies ("10.07.2026", "Метро") classify as unknown and are still continuations.
    return new_type == "unknown"


def continue_pending_entry(entry: ExtractedEntry, text: str | None) -> ExtractedEntry:
    """Extract new values from a follow-up message and merge them into the current pending entry."""
    if not text:
        return entry

    normalized = text.strip()
    if not normalized:
        return entry

    payload: dict[str, Any] = dict(parse_follow_up_fields(normalized))

    # Fallback: loose date extraction (e.g., 10.07.2026)
    if "expiry_date" not in payload:
        date_match = re.search(r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", normalized)
        if date_match:
            payload["expiry_date"] = date_match.group(1)

    # If nothing was parsed from the text, try an LLM fallback when configured
    if not payload:
        settings = None
        try:
            settings = get_settings()
        except Exception:
            settings = None

        if ChatOpenAI and settings and getattr(settings, "openai_api_key", None):
            try:
                llm_payload = _invoke_llm_followup(normalized, entry.entry_type)
                if isinstance(llm_payload, dict):
                    payload.update(llm_payload)
            except Exception:
                # Swallow LLM errors; fallback remains a no-op
                pass

    return merge_pending_entry(entry, payload)


def _invoke_llm_followup(text: str, entry_type: str) -> dict[str, Any] | None:
    """Use the configured LLM to parse a follow-up message into diary fields.

    This is a best-effort fallback for ambiguous short follow-ups. It returns
    a flat mapping of field -> value suitable for `merge_pending_entry`.
    """
    settings = get_settings()
    if not getattr(settings, "openai_api_key", None):
        return None

    # Simple in-memory cache for follow-up LLM responses
    global _LLM_CACHE, _LAST_LLM_CALL
    try:
        ttl = int(getattr(settings, "pending_ttl_seconds", 600))
    except Exception:
        ttl = 600

    now = time.time()
    key = json.dumps({"text": text, "entry_type": entry_type}, sort_keys=True, ensure_ascii=False)
    cached = _LLM_CACHE.get(key)
    if cached:
        ts, value = cached
        if now - ts < ttl:
            return value

    # Rate-limiting: small sleep to avoid bursts
    MIN_INTERVAL = 0.5
    elapsed = now - _LAST_LLM_CALL
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)

    diaries = None
    try:
        diaries = get_diaries()
    except Exception:
        diaries = {}

    diary = diaries.get(entry_type) if diaries else None
    required = []
    if diary is not None:
        required = getattr(diary, "required_fields", [])

    required_hint = f"Prefer these required fields: {', '.join(required)}." if required else ""

    prompt = (
        f"You are an assistant that extracts missing fields for a HACCP diary entry (type: {entry_type}).\n"
        f"{required_hint}\n"
        f"User follow-up message: '{text}'\n"
        "Return ONLY a flat JSON object mapping field names to values, for example:\n"
        "{\"expiry_date\": \"10.07.2026\"}\n"
        "If you cannot extract anything, return an empty JSON object {}."
    )
    # Import locally to avoid circular module initialization during tests
    from haccp.graph.nodes.extraction import parse_llm_json_response

    # Call low-level wrapper so tests can monkeypatch the actual network call
    response_text = _call_llm_raw(prompt)
    parsed = parse_llm_json_response(response_text)
    if isinstance(parsed, dict):
        _LLM_CACHE[key] = (time.time(), parsed)
        _LAST_LLM_CALL = time.time()
        return parsed
    return None


def _call_llm_raw(prompt: str) -> str:
    """Low-level wrapper to call the LLM and return raw text content. Exposed
    so tests can monkeypatch it easily."""
    settings = get_settings()
    llm = ChatOpenAI(model=settings.openai_model, temperature=0)
    response = llm.invoke(prompt)
    return str(response.content)


def _clear_llm_cache() -> None:
    global _LLM_CACHE, _LAST_LLM_CALL
    _LLM_CACHE.clear()
    _LAST_LLM_CALL = 0.0


def merge_pending_entry(entry: ExtractedEntry, payload: dict[str, Any]) -> ExtractedEntry:
    """Merge a new payload with an existing extracted entry when continuing a pending diary entry."""
    for key, value in payload.items():
        if value is None:
            continue
        if key == "entry_type":
            continue
        current_value = getattr(entry, key, None)
        if current_value in {None, "", "неизвестна", "неизвестен", "unknown", "n/a"} or str(current_value) == "Старо":
            setattr(entry, key, value)
    return entry


def handle_pending(state: dict[str, Any], *, db_path: str | None = None) -> dict[str, Any]:
    """Persist incomplete entries and prepare a follow-up message when required fields are missing."""
    entry = state.get("extracted")
    if not isinstance(entry, ExtractedEntry):
        state["pending_handled"] = True
        state["reply_messages"] = state.get("reply_messages", []) + ["Няма какво да продължим."]
        return state

    errors = state.get("validation_errors") or []
    if not errors:
        state["pending_handled"] = True
        return state

    missing = [MissingField(field=field, label=field) for field in errors]
    chat_id = str(state.get("chat_id") or "unknown")
    save_pending_entry(entry, missing_fields=errors, chat_id=chat_id, db_path=db_path)

    state["pending_handled"] = True
    state["reply_messages"] = state.get("reply_messages", []) + [
        f"Записът е готов, но има липсващи полета: {', '.join(errors)}. Моля, изпратете допълнителни данни."
    ]
    return state
