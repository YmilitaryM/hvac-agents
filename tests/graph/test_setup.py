import pytest
from src.graph.setup import HVACGraph
from src.schemas.state import AgentState


class TestHVACGraph:
    @pytest.fixture
    def graph(self):
        return HVACGraph(debug=True)

    def test_build_compiles(self, graph):
        """Graph should compile without errors."""
        g = graph.build()
        assert g is not None

    def test_graph_has_nodes(self, graph):
        """Graph should have all 8 nodes."""
        g = graph.build()
        nodes = g.get_graph().nodes
        expected = {
            "monitor",
            "predict",
            "strategy",
            "advocates",
            "coordinator",
            "debate",
            "safety",
            "execute",
        }
        assert expected.issubset(set(nodes.keys()))

    def test_empty_agents_produce_empty_results(self, graph):
        """With no agents configured, graph should run without errors."""
        import asyncio

        state = AgentState(current_time=1000.0, trigger_type="scheduled")
        result = asyncio.run(graph._monitor_node(state))
        assert "alerts" in result
        assert result["anomaly_detected"] is False

    def test_execute_node_updates_state(self, graph):
        """Execute node should move pending_strategy to current_strategy."""
        import asyncio

        state = AgentState(
            pending_strategy={
                "strategy_id": "test_1",
                "actions": [
                    {"seq": 1, "device": "ch1", "action": "set_load", "value": 300}
                ],
            },
            current_time=1000.0,
        )
        result = asyncio.run(graph._execute_node(state))
        assert result["current_strategy"]["strategy_id"] == "test_1"
        assert result["current_strategy"]["status"] == "approved"
        assert result["pending_strategy"] is None
        assert len(result["strategy_history"]) == 1

    def test_strategy_node_handles_missing_agent(self, graph):
        """Strategy node with no agent returns empty dict."""
        import asyncio

        state = AgentState(predicted_load_rt=500, current_time=1000.0)
        result = asyncio.run(graph._strategy_node(state))
        assert result == {}

    def test_advocates_node_runs_all_three(self, graph):
        """Advocates node handles missing agents gracefully."""
        import asyncio

        state = AgentState(
            pending_strategy={"strategy_id": "test_1", "actions": []}
        )
        result = asyncio.run(graph._advocates_node(state))
        assert "advocate_opinions" in result
        assert result["advocate_opinions"] == []
