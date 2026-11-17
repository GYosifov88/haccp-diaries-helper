from __future__ import annotations

from haccp.graph import graph as graph_module
from haccp.graph.nodes.pending import load_pending_entry

CHAT_ID = "123"

MESSAGE_1 = "Доставка от Метро: пилешко филе 20 кг, температура 3°C, опаковка цяла, фактура 12345, прието"
MESSAGE_2 = "срок на годност 10.07.2026"

MESSAGE_1_OUTPUT = {
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


def test_two_message_continuation_writes_merged_entry_once(offline) -> None:
    offline["llm_outputs"].append(("Метро", MESSAGE_1_OUTPUT))
    _payload = offline["payload"]
    sheets_calls = offline["sheets_calls"]

    # --- Run 1: incomplete entry -> bot asks for the missing field ---
    first = graph_module.run_workflow(_payload(CHAT_ID, MESSAGE_1))

    assert first["validation_errors"] == ["expiry_date"]
    assert sheets_calls == []
    stored = load_pending_entry(chat_id=CHAT_ID)
    assert stored is not None
    assert [m.field for m in stored.missing] == ["expiry_date"]
    assert stored.entry is not None and stored.entry.supplier == "Метро"
    first_date = first["extracted"].date
    prompts_before_reply = len(offline["extraction_prompts"])

    # --- Run 2: user replies with the missing field ---
    second = graph_module.run_workflow(_payload(CHAT_ID, MESSAGE_2))

    assert len(sheets_calls) == 1
    written, _signature = sheets_calls[0]
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
    assert len(sheets_calls) == 1
