from __future__ import annotations

from haccp.graph import graph as graph_module
from haccp.graph.nodes.pending import load_pending_entry

NO_ACCESS = "Нямате достъп до този бот."
STRANGER = "666"

MESSAGE_COMPLETE = (
    "Доставка от Билла: мляко 5 л, температура 4, опаковка цяла, "
    "фактура 777, срок на годност 20.11.2026, прието"
)
COMPLETE_OUTPUT = {
    "output": {
        "entry_type": "incoming_goods",
        "supplier": "Билла",
        "product": "мляко",
        "quantity": "5",
        "unit": "л",
        "temperature": "4",
        "package_condition": "цяла",
        "documents": "фактура 777",
        "decision": "прието",
        "expiry_date": "20.11.2026",
    }
}

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


def test_unauthorized_sender_is_short_circuited(offline) -> None:
    offline["llm_outputs"].append(("Билла", COMPLETE_OUTPUT))
    offline["llm_outputs"].append(("Метро", MESSAGE_1_OUTPUT))
    payload = offline["payload"]
    sheets_calls = offline["sheets_calls"]
    prompts = offline["extraction_prompts"]

    # --- Denied, complete message: would be written if it were processed ---
    denied_write = graph_module.run_workflow(payload("401", MESSAGE_COMPLETE, user_id=STRANGER))
    assert len(sheets_calls) == 0
    assert prompts == []
    assert denied_write["reply_messages"] == [NO_ACCESS]
    assert denied_write["access_denied"] is True

    # --- Denied, incomplete message: would save a pending row if it were processed ---
    denied_pending = graph_module.run_workflow(payload("402", MESSAGE_1, user_id=STRANGER))
    assert load_pending_entry(chat_id="402") is None
    assert prompts == []
    assert denied_pending["reply_messages"] == [NO_ACCESS]
    assert len(sheets_calls) == 0

    # --- Control: an authorized sender is processed normally ---
    allowed_write = graph_module.run_workflow(payload("403", MESSAGE_COMPLETE))
    assert len(sheets_calls) == 1
    assert allowed_write["reply_messages"][0].startswith("Записът е записан")

    graph_module.run_workflow(payload("404", MESSAGE_1))
    assert load_pending_entry(chat_id="404") is not None
