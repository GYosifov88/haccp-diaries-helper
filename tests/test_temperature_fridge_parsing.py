from haccp.graph.nodes.extraction import _build_entry


def test_fridge_temperature_parsing_prefers_value_after_fridge_number() -> None:
    entry = _build_entry(
        "temperature_fridge",
        text="температура на хладилник 3 е 4гр в 17:35",
        signature="Иван",
    )

    assert entry.fridge_number == "3"
    assert entry.temperature == "4"
