from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from haccp.config import get_users
from haccp.models.state import GraphState, TelegramUser
from haccp.graph.nodes.extraction import extract_entry
from haccp.graph.nodes.validation import validate_entry
from haccp.graph.nodes.classification import classify_entry_type
from haccp.graph.nodes.pending import clear_pending_entry, handle_pending, load_pending_entry, should_continue_pending_entry
from haccp.graph.nodes.response import build_response_message
from haccp.graph.nodes.follow_up import build_follow_up_message
from haccp.services.sheets import SheetsService


def resolve_user(state: dict[str, Any]) -> dict[str, Any]:
    telegram_user_id = state.get("telegram_user_id") or ""
    chat_id = state.get("chat_id") or telegram_user_id
    users = get_users()
    mapped_name = users.get(telegram_user_id)
    display_name = state.get("telegram_user_name")
    signature = display_name or mapped_name or "Unknown"
    state["user"] = TelegramUser(
        user_id=telegram_user_id,
        chat_id=chat_id,
        name=mapped_name or signature,
        signature=signature,
        allowed=bool(telegram_user_id),
    )
    state["access_denied"] = not bool(telegram_user_id)

    pending = load_pending_entry(chat_id=chat_id)
    if pending is not None:
        state["pending_handled"] = True
        state["validation_errors"] = [item.field for item in pending.missing]
        state["raw_text"] = state.get("raw_text") or state.get("input_text") or ""
        state["pending_entry"] = pending.entry
    return state


def classify_node(state: dict[str, Any]) -> dict[str, Any]:
    text = state.get("raw_text") or state.get("input_text") or ""
    state["entry_type"] = classify_entry_type(text)
    state["help_requested"] = should_continue_pending_entry(text)
    return state


def write_entry(state: dict[str, Any]) -> dict[str, Any]:
    entry = state.get("extracted")
    if not entry:
        state["reply_messages"] = ["Неуспешно извличане на данни."]
        state["finished"] = True
        return state

    try:
        writer = SheetsService()
        written_entries = writer.append_entry(
            entry,
            signature=state.get("user").signature if state.get("user") else "неизвестен",
        )
    except Exception as exc:  # pragma: no cover - runtime dependent
        state["validation_errors"] = [str(exc)]
        state["reply_messages"] = [f"Записът е подготвен, но не можа да бъде записан: {exc}"]
        state["finished"] = True
        return state

    try:
        clear_pending_entry(chat_id=str(state.get("chat_id") or ""))
    except Exception:  # pragma: no cover - a failed cleanup must not fail a successful write
        pass

    state["written_entries"] = written_entries
    state["reply_messages"] = [build_response_message(entry, missing_fields=[], written=True)]
    state["finished"] = True
    return state


def finalize(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("access_denied"):
        state["reply_messages"] = ["Нямате достъп до този бот."]
    elif state.get("validation_errors"):
        entry = state.get("extracted")
        if entry is not None:
            state["reply_messages"] = [
                build_follow_up_message(entry.entry_type, list(state.get("validation_errors", [])))
            ]
        else:
            state["reply_messages"] = ["Извличането е готово, но има липсващи полета: " + ", ".join(state["validation_errors"])]
    state["finished"] = True
    return state


def build_graph() -> Any:
    workflow = StateGraph(GraphState)
    workflow.add_node("resolve_user", resolve_user)
    workflow.add_node("classify", classify_node)
    workflow.add_node("extract", extract_entry)
    workflow.add_node("validate", validate_entry)
    workflow.add_node("write", write_entry)
    workflow.add_node("pending", handle_pending)
    workflow.add_node("finalize", finalize)

    workflow.set_entry_point("resolve_user")
    workflow.add_edge("resolve_user", "classify")
    workflow.add_edge("classify", "extract")
    workflow.add_edge("extract", "validate")
    workflow.add_conditional_edges(
        "validate",
        lambda state: "pending" if state.get("validation_errors") else "write",
        {
            "pending": "pending",
            "write": "write",
        },
    )
    workflow.add_edge("write", "finalize")
    workflow.add_edge("pending", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()


def run_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    graph = build_graph()
    initial_state: GraphState = {
        "telegram_user_id": payload.get("telegram_user_id", ""),
        "chat_id": payload.get("chat_id", payload.get("telegram_user_id", "")),
        "telegram_user_name": payload.get("telegram_user_name"),
        "input_kind": payload.get("input_kind", "text"),
        "raw_text": payload.get("raw_text") or payload.get("input_text"),
        "file_bytes": payload.get("file_bytes"),
        "file_mime": payload.get("file_mime"),
        "reply_messages": [],
        "finished": False,
        "access_denied": False,
        "help_requested": False,
        "pending_handled": False,
        "pending_entry": None,
        "entries_to_write": [],
        "written_entries": [],
        "validation_errors": [],
    }
    return graph.invoke(initial_state)
