from __future__ import annotations

from typing import Any

from haccp.config import get_classification_hints


def _keyword_score(text: str, keywords: list[str]) -> int:
    return sum(text.count(keyword) for keyword in keywords)


def classify_entry_type(text: str | None) -> str:
    """Return a diary entry type based on the incoming message."""
    if not text:
        return "unknown"

    normalized = text.lower().strip()
    hints = get_classification_hints()
    scores: dict[str, int] = {}

    for entry_type, keywords in hints.items():
        scores[entry_type] = _keyword_score(normalized, keywords)

    extra_keywords: dict[str, list[str]] = {
        "temperature_fridge": ["хладилник", "фризер", "градус", "температура", "охлаждане"],
        "temperature_thermal": ["термична обработка", "готвене", "изпичане", "варене", "ядро", "термична", "вътрешна температура", "температура на продукта"],
        "incoming_goods": ["фактура", "доставчик", "доставих", "приемане", "доставка", "продукт", "партида", "срок на годност", "входящ контрол", "стоки"],
        "cleaning": ["почистване", "дезинфекция", "измиване", "почистен", "чист", "мокро почистване", "дезинфекцира"],
        "personal_hygiene": ["хигиена", "ръце", "облекло", "бижута", "униформа", "измити ръце", "чисто облекло", "без бижута"],
        "waste": ["отпадък", "отпадъци", "боклук", "изхвърли", "изхвърлен", "изхвърлени", "изхвърляне", "комунален", "контейнер", "битов"],
        "pest_control": ["вредител", "миш", "хлебарка", "плъх", "дератизация", "дезинсекция", "пръскане", "инспекция"],
        "equipment_control": ["оборудване", "уред", "машина", "не работи", "работи", "счупен", "ремонт"],
        "water_control": ["вода", "чешма", "сертификат", "източник", "проби", "пречистване"],
        "ddd": ["ддд", "дератиза", "дезинсекция", "дезинфекция", "пръскане", "обработка"],
        "traceability": ["проследимост", "партида", "batch", "серий", "произход", "доставчик"],
        "complaints": ["рекламация", "оплакване", "жалба", "клиент", "недоволство"],
    }

    for entry_type, keywords in extra_keywords.items():
        scores[entry_type] = scores.get(entry_type, 0) + _keyword_score(normalized, keywords)

    best_match = max(scores.items(), key=lambda item: item[1])
    if best_match[1] > 0:
        return best_match[0]

    return "unknown"
