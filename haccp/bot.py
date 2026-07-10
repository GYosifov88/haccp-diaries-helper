from __future__ import annotations

from typing import Any

from haccp.graph.graph import run_workflow


def build_payload(
    *,
    user_id: str,
    chat_id: str,
    user_name: str | None = None,
    text: str | None = None,
    input_kind: str = "text",
    file_bytes: bytes | None = None,
    file_mime: str | None = None,
) -> dict[str, Any]:
    return {
        "telegram_user_id": user_id,
        "chat_id": chat_id,
        "telegram_user_name": user_name,
        "input_kind": input_kind,
        "raw_text": text,
        "input_text": text,
        "file_bytes": file_bytes,
        "file_mime": file_mime,
    }


def handle_message(
    *,
    user_id: str,
    chat_id: str,
    user_name: str | None = None,
    text: str | None = None,
    input_kind: str = "text",
    file_bytes: bytes | None = None,
    file_mime: str | None = None,
) -> dict[str, Any]:
    payload = build_payload(
        user_id=user_id,
        chat_id=chat_id,
        user_name=user_name,
        text=text,
        input_kind=input_kind,
        file_bytes=file_bytes,
        file_mime=file_mime,
    )
    return run_workflow(payload)
