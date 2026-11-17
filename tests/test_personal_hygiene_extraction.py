from haccp.graph.nodes.extraction import _build_entry
from haccp.graph.graph import run_workflow


def test_personal_hygiene_message_parses_employee_and_hygiene_flags() -> None:
    entry = _build_entry(
        "personal_hygiene",
        text="Георги започна работа с чисто облекло, измити ръце и без бижута",
        signature="Иван",
    )

    assert entry.employee == "Георги"
    assert entry.clean_uniform == "да"
    assert entry.washed_hands == "да"
    assert entry.no_jewelry == "да"


def test_personal_hygiene_workflow_roundtrip(offline) -> None:
    offline["users"]["123"] = "Георги"
    # The LLM returns nothing usable, so extraction falls back to the regex path.
    offline["llm_outputs"].append(("Георги", {}))

    result = run_workflow({
        "telegram_user_id": "123",
        "chat_id": "123",
        "telegram_user_name": "Георги",
        "input_kind": "text",
        "raw_text": "Георги започна работа с чисто облекло, измити ръце и без бижута",
        "input_text": "Георги започна работа с чисто облекло, измити ръце и без бижута",
    })

    assert result["user"].signature == "Георги"
    assert result["extracted"].entry_type == "personal_hygiene"
    assert result["extracted"].employee == "Георги"
    assert result["extracted"].clean_uniform == "да"
    assert result["extracted"].washed_hands == "да"
    assert result["extracted"].no_jewelry == "да"
    assert result["validation_errors"] == []
