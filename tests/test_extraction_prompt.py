from haccp.graph.nodes.extraction import build_extraction_prompt, parse_llm_json_response


def test_build_extraction_prompt_includes_signature_and_schema() -> None:
    prompt = build_extraction_prompt("incoming_goods", "купихме стоки за фактура", "Иван")

    assert "incoming_goods" in prompt
    assert "Иван" in prompt
    assert "signature" in prompt.lower()


def test_parse_llm_json_response_extracts_json_from_code_block() -> None:
    response = '```json\n{"output": {"entry_type": "incoming_goods", "supplier": "Тест"}}\n```'

    parsed = parse_llm_json_response(response)

    assert parsed is not None
    assert parsed["output"]["entry_type"] == "incoming_goods"
    assert parsed["output"]["supplier"] == "Тест"
