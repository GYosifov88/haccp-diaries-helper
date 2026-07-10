from haccp.graph.nodes.extraction import _build_entry


def test_waste_message_parses_quantity_and_container() -> None:
    entry = _build_entry(
        "waste",
        text="изхвърлени 3 чувала боклук в контейнерите за битов отпадък. Веселин ги изхвърли",
        signature="Иван",
    )

    assert entry.waste_type == "боклук"
    assert entry.quantity == "3 бр"
    assert entry.container is not None
    assert "контейнер" in entry.container
    assert entry.disposed_where is not None


def test_waste_message_with_bитов_отпадък_parses_quantity() -> None:
    entry = _build_entry(
        "waste",
        text="Веселин изхвърли 3 чувала битов отпадък в контейнерите за битов отпадък",
        signature="Иван",
    )

    assert entry.waste_type == "боклук"
    assert entry.quantity == "3 бр"
    assert entry.container == "контейнерите за битов отпадък"
    assert entry.disposed_where == "контейнерите"
