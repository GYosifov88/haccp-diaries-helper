from haccp.graph.nodes.classification import classify_entry_type


def test_classify_incoming_goods_keywords() -> None:
    assert classify_entry_type("купихме стоки и фактура") == "incoming_goods"


def test_classify_fridge_temperature() -> None:
    assert classify_entry_type("температура в хладилник 2 е 3.5") == "temperature_fridge"


def test_unknown_returns_unknown() -> None:
    assert classify_entry_type("hello there") == "unknown"
