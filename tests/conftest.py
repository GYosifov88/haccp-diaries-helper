from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from haccp import config
from haccp.config import get_settings
from haccp.graph import graph as graph_module
from haccp.graph.nodes import extraction, pending
from haccp.models.state import WrittenEntry

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def isolated_pending_db(tmp_path, monkeypatch):
    """Keep tests off the real ./data/haccp.db so pending entries never leak between tests."""
    monkeypatch.setattr(get_settings(), "sqlite_path", str(tmp_path / "haccp.db"))


class FakeSheetsService:
    """Records append_entry calls instead of talking to Google Sheets."""

    calls: list[tuple[Any, str]] = []

    def append_entry(self, entry, *, signature: str):
        FakeSheetsService.calls.append((entry.model_copy(deep=True), signature))
        return [
            WrittenEntry(
                entry_id="e1",
                entry_type=entry.entry_type,
                sheet_name="fake",
                row_number=1,
                data={},
            )
        ]


def make_payload(chat_id: str, text: str) -> dict[str, Any]:
    return {
        "telegram_user_id": chat_id,
        "chat_id": chat_id,
        "telegram_user_name": "Иван",
        "input_kind": "text",
        "raw_text": text,
        "input_text": text,
    }


# What a real model returns when it only sees a short reply: the new value plus
# "unknown" for everything else.
REPLY_ONLY_OUTPUT: dict[str, Any] = {
    "output": {
        "entry_type": "incoming_goods",
        "supplier": "неизвестна",
        "product": "неизвестна",
        "quantity": "неизвестна",
        "unit": "неизвестна",
        "temperature": "неизвестна",
        "package_condition": "неизвестна",
        "documents": "неизвестна",
        "decision": "неизвестна",
        "expiry_date": "10.07.2026",
    }
}


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """Opt-in fixture that makes run_workflow fully offline.

    - real SQLite pending store in a temp dir, settings built without .env
    - fake extraction LLM driven by ``offline["llm_outputs"]``: a list of
      (substring, output) pairs matched in order against the prompt; when nothing
      matches the reply-only placeholder is returned
    - fake follow-up LLM (returns "{}", calls recorded)
    - fake Sheets service (calls recorded in ``offline["sheets_calls"]``)
    """
    settings = config.Settings(
        openai_api_key="test",
        telegram_bot_token="x",
        google_spreadsheet_id="x",
        sqlite_path=str(tmp_path / "haccp.db"),
        diaries_config_path=str(REPO_ROOT / "config" / "diaries.yaml"),
    )
    monkeypatch.setattr(config, "_settings", settings)
    monkeypatch.setattr(config, "_diaries", None)
    monkeypatch.setattr(config, "_classification_hints", None)
    monkeypatch.setattr(graph_module, "get_users", lambda: {})
    pending._clear_llm_cache()

    llm_outputs: list[tuple[str, dict[str, Any]]] = []
    extraction_prompts: list[str] = []
    followup_llm_calls: list[str] = []

    def fake_extraction_llm(prompt: str, *, entry_type: str):
        extraction_prompts.append(prompt)
        for substring, output in llm_outputs:
            if substring in prompt:
                return output
        return REPLY_ONLY_OUTPUT

    def fake_followup_llm(prompt: str) -> str:
        followup_llm_calls.append(prompt)
        return "{}"

    monkeypatch.setattr(extraction, "_invoke_llm_extraction", fake_extraction_llm)
    monkeypatch.setattr(pending, "_call_llm_raw", fake_followup_llm)
    FakeSheetsService.calls = []
    monkeypatch.setattr(graph_module, "SheetsService", FakeSheetsService)

    return {
        "llm_outputs": llm_outputs,
        "extraction_prompts": extraction_prompts,
        "followup_llm_calls": followup_llm_calls,
        "sheets_calls": FakeSheetsService.calls,
        "payload": make_payload,
    }
