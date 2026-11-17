from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from haccp import config
from haccp.graph import graph as graph_module
from haccp.graph.nodes import extraction, pending
from haccp.graph.nodes.pending import load_pending_entry
from haccp.models.state import WrittenEntry

REPO_ROOT = Path(__file__).resolve().parent.parent
CHAT_ID = "123"

MESSAGE_1 = "Доставка от Метро: пилешко филе 20 кг, температура 3°C, опаковка цяла, фактура 12345, прието"
MESSAGE_2 = "срок на годност 10.07.2026"


class FakeSheetsService:
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


@pytest.fixture
def offline(monkeypatch, tmp_path):
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

    extraction_prompts: list[str] = []
    followup_llm_calls: list[str] = []

    def fake_extraction_llm(prompt: str, *, entry_type: str):
        extraction_prompts.append(prompt)
        if "Метро" in prompt:
            return {
                "output": {
                    "entry_type": "incoming_goods",
                    "supplier": "Метро",
                    "product": "пилешко филе",
                    "quantity": "20",
                    "unit": "кг",
                    "temperature": "3",
                    "package_condition": "цяла",
                    "documents": "фактура 12345",
                    "decision": "прието",
                    "expiry_date": "неизвестна",
                }
            }
        # What a real model returns when it only sees the short reply:
        # the new value plus "unknown" for everything else.
        return {
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

    def fake_followup_llm(prompt: str) -> str:
        followup_llm_calls.append(prompt)
        return "{}"

    monkeypatch.setattr(extraction, "_invoke_llm_extraction", fake_extraction_llm)
    monkeypatch.setattr(pending, "_call_llm_raw", fake_followup_llm)
    FakeSheetsService.calls = []
    monkeypatch.setattr(graph_module, "SheetsService", FakeSheetsService)

    return {"extraction_prompts": extraction_prompts, "followup_llm_calls": followup_llm_calls}


def _payload(chat_id: str, text: str) -> dict[str, Any]:
    return {
        "telegram_user_id": chat_id,
        "chat_id": chat_id,
        "telegram_user_name": "Иван",
        "input_kind": "text",
        "raw_text": text,
        "input_text": text,
    }


def test_two_message_continuation_writes_merged_entry_once(offline) -> None:
    # --- Run 1: incomplete entry -> bot asks for the missing field ---
    first = graph_module.run_workflow(_payload(CHAT_ID, MESSAGE_1))

    assert first["validation_errors"] == ["expiry_date"]
    assert FakeSheetsService.calls == []
    stored = load_pending_entry(chat_id=CHAT_ID)
    assert stored is not None
    assert [m.field for m in stored.missing] == ["expiry_date"]
    assert stored.entry is not None and stored.entry.supplier == "Метро"
    first_date = first["extracted"].date
    prompts_before_reply = len(offline["extraction_prompts"])

    # --- Run 2: user replies with the missing field ---
    second = graph_module.run_workflow(_payload(CHAT_ID, MESSAGE_2))

    assert len(FakeSheetsService.calls) == 1
    written, _signature = FakeSheetsService.calls[0]
    assert written.entry_type == "incoming_goods"
    assert written.supplier == "Метро"
    assert written.product == "пилешко филе"
    assert str(written.quantity) == "20"
    assert written.unit == "кг"
    assert str(written.temperature) == "3"
    assert written.documents == "фактура 12345"
    assert written.decision == "прието"
    assert written.expiry_date == "10.07.2026"
    assert written.date == first_date  # expiry date must not leak into the entry date

    assert second["validation_errors"] == []
    assert second["written_entries"]
    assert load_pending_entry(chat_id=CHAT_ID) is None

    # Continuation must not use the full-extraction LLM or the follow-up LLM fallback.
    assert len(offline["extraction_prompts"]) == prompts_before_reply
    assert offline["followup_llm_calls"] == []

    # --- Control: the same reply with no pending entry cannot be written ---
    control = graph_module.run_workflow(_payload("999", MESSAGE_2))
    assert control["validation_errors"]
    assert len(FakeSheetsService.calls) == 1
