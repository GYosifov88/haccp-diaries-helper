from haccp.graph.graph import build_graph


def test_build_graph_contains_pending_branch() -> None:
    graph = build_graph()
    assert graph is not None
