from haccp.graph.nodes.extraction import build_extraction_prompt


def test_build_extraction_prompt_uses_diary_specific_schema() -> None:
    prompt = build_extraction_prompt(
        "incoming_goods",
        "купихме стоки и фактура",
        "Иван",
    )

    assert "incoming_goods" in prompt
    assert "supplier" in prompt.lower()
    assert "decision" in prompt.lower()
    assert "Иван" in prompt
