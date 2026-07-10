from haccp.graph.nodes.follow_up import build_follow_up_message


def test_build_follow_up_message_lists_missing_fields() -> None:
    message = build_follow_up_message("incoming_goods", ["supplier", "expiry_date"])

    assert "incoming_goods" in message
    assert "supplier" in message
    assert "expiry_date" in message
