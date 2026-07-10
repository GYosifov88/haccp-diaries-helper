from haccp.graph.nodes.pending import should_continue_pending_entry


def test_should_continue_pending_entry_detects_follow_up() -> None:
    assert should_continue_pending_entry("продължи") is True
    assert should_continue_pending_entry("добави срок на годност") is True
    assert should_continue_pending_entry("нов запис") is False
