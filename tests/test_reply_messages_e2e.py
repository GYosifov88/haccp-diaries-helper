from __future__ import annotations

from collections import Counter

from haccp.graph import graph as graph_module

MESSAGE_COMPLETE = (
    "Доставка от Билла: мляко 5 л, температура 4, опаковка цяла, "
    "фактура 777, срок на годност 20.11.2026, прието"
)
MESSAGE_COMPLETE_OUTPUT = {
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

MESSAGE_INCOMPLETE = "Доставка от Метро: пилешко филе 20 кг, температура 3°C, опаковка цяла, фактура 12345, прието"
MESSAGE_INCOMPLETE_OUTPUT = {
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


def test_each_run_produces_a_single_reply(offline) -> None:
    offline["llm_outputs"].append(("Билла", MESSAGE_COMPLETE_OUTPUT))
    offline["llm_outputs"].append(("Метро", MESSAGE_INCOMPLETE_OUTPUT))
    payload = offline["payload"]
    sheets_calls = offline["sheets_calls"]

    problems: list[str] = []

    # --- Scenario A: write path ---
    write_result = graph_module.run_workflow(payload("201", MESSAGE_COMPLETE))
    write_replies = write_result["reply_messages"]
    if len(sheets_calls) != 1:
        problems.append(f"A: expected exactly 1 Sheets call, got {len(sheets_calls)}")
    if len(write_replies) != 1:
        problems.append(f"A: expected 1 reply, got {len(write_replies)}: {write_replies!r}")
    if not (write_replies and write_replies[0].startswith("Записът е записан")):
        problems.append(f"A: first reply should start with 'Записът е записан': {write_replies!r}")
    if any(count != 1 for count in Counter(write_replies).values()):
        problems.append(f"A: a reply is repeated: {write_replies!r}")

    # --- Scenario B: pending path ---
    pending_result = graph_module.run_workflow(payload("202", MESSAGE_INCOMPLETE))
    pending_replies = pending_result["reply_messages"]
    if pending_result["validation_errors"] != ["expiry_date"]:
        problems.append(f"B: expected only expiry_date missing, got {pending_result['validation_errors']!r}")
    if len(pending_replies) != 1:
        problems.append(f"B: expected 1 reply, got {len(pending_replies)}: {pending_replies!r}")
    if not (pending_replies and "expiry_date" in pending_replies[0] and "Имате незавършен запис" in pending_replies[0]):
        problems.append(f"B: the single reply should be the follow-up naming expiry_date: {pending_replies!r}")

    assert not problems, "\n".join(problems)
