from __future__ import annotations

from haccp.graph import graph as graph_module
from haccp.graph.nodes.pending import load_pending_entry

MESSAGE_1 = "Доставка от Метро: пилешко филе 20 кг, температура 3°C, опаковка цяла, фактура 12345, прието"
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

MESSAGE_B = "Хладилник 2 температура 3 градуса"
MESSAGE_B_OUTPUT = {
    "output": {
        "entry_type": "temperature_fridge",
        "fridge_number": "2",
        "temperature": "3",
    }
}

REPLY = "срок на годност 10.07.2026"


def test_different_type_message_abandons_pending_and_writes_own_entry(offline) -> None:
    offline["llm_outputs"].append(("Метро", MESSAGE_1_OUTPUT))
    offline["llm_outputs"].append(("Хладилник 2", MESSAGE_B_OUTPUT))
    payload = offline["payload"]
    sheets_calls = offline["sheets_calls"]

    # --- Step 1: incomplete entry A leaves a pending row ---
    graph_module.run_workflow(payload("301", MESSAGE_1))
    stored = load_pending_entry(chat_id="301")
    assert stored is not None
    assert [m.field for m in stored.missing] == ["expiry_date"]
    assert sheets_calls == []

    # --- Step 2: a clearly different message B starts its own entry ---
    result = graph_module.run_workflow(payload("301", MESSAGE_B))

    assert len(sheets_calls) == 1
    written, _signature = sheets_calls[0]
    assert written.entry_type == "temperature_fridge"
    assert written.fridge_number == "2"
    assert str(written.temperature) == "3"
    # nothing from A leaks into B
    assert written.supplier is None
    assert written.product is None
    assert written.documents is None
    assert written.package_condition is None
    assert written.expiry_date is None

    assert load_pending_entry(chat_id="301") is None
    assert any("Хладилник 2" in prompt for prompt in offline["extraction_prompts"])

    replies = result["reply_messages"]
    assert "отказан" in replies[0] and "incoming_goods" in replies[0]
    assert replies[1].startswith("Записът е записан")

    # --- Control: a real follow-up still merges and is not reported as abandoned ---
    graph_module.run_workflow(payload("302", MESSAGE_1))
    control = graph_module.run_workflow(payload("302", REPLY))

    assert len(sheets_calls) == 2
    latest, _signature = sheets_calls[-1]
    assert latest.entry_type == "incoming_goods"
    assert latest.supplier == "Метро"
    assert latest.expiry_date == "10.07.2026"
    assert not any("отказан" in reply for reply in control["reply_messages"])
