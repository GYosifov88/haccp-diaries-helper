from haccp.graph.nodes.classification import classify_entry_type


def test_classify_incoming_goods_ocr_text() -> None:
    text = "Получихме стоки от доставчик със срок на годност 10.07.2026 и фактура №123"
    assert classify_entry_type(text) == "incoming_goods"


def test_classify_temperature_thermal_text() -> None:
    text = "Ядрената температура на продукта при термична обработка е 75°C"
    assert classify_entry_type(text) == "temperature_thermal"


def test_classify_pest_control_text() -> None:
    text = "Открити са хлебарки и предстои дезинсекция"
    assert classify_entry_type(text) == "pest_control"


def test_classify_waste_message_text() -> None:
    text = "Веселин изхвърли 3 чувала битов отпадък в контейнерите за битов отпадък"
    assert classify_entry_type(text) == "waste"
