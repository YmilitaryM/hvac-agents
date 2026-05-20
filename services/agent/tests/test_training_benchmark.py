import asyncio

import pytest

from agent_service.rl.benchmark.comparator import BenchmarkResult, Comparator
from agent_service.rl.training.online_finetune import OnlineFinetuner


def test_benchmark_comparator():
    mappo = BenchmarkResult(
        method="mappo", total_cost=8500.0, avg_cop=5.8,
        carbon_tonnes=120.0, comfort_violations=3, load_match_pct=0.94,
    )
    milp = BenchmarkResult(
        method="milp_only", total_cost=9200.0, avg_cop=5.5,
        carbon_tonnes=130.0, comfort_violations=5, load_match_pct=0.90,
    )
    pid = BenchmarkResult(
        method="pid", total_cost=10000.0, avg_cop=5.0,
        carbon_tonnes=145.0, comfort_violations=8, load_match_pct=0.85,
    )

    comparator = Comparator()
    report = comparator.compare(mappo, [milp, pid])

    assert report["mappo"]["cost"] == 8500.0
    assert report["mappo"]["cop"] == 5.8
    assert len(report["baselines"]) == 2
    assert report["baselines"][0]["method"] == "milp_only"
    assert report["mappo_savings_pct"] == 0.0  # mappo is cheapest


def test_benchmark_comparator_worse_than_baseline():
    """When mappo is worst, savings_pct should be negative."""
    mappo = BenchmarkResult(
        method="mappo", total_cost=11000.0, avg_cop=4.5,
        carbon_tonnes=150.0, comfort_violations=2, load_match_pct=0.80,
    )
    milp = BenchmarkResult(
        method="milp_only", total_cost=9000.0, avg_cop=5.5,
        carbon_tonnes=130.0, comfort_violations=5, load_match_pct=0.90,
    )

    comparator = Comparator()
    report = comparator.compare(mappo, [milp])
    assert report["mappo_savings_pct"] < 0


def test_online_finetuner_buffer():
    ft = OnlineFinetuner(controller=None, learning_rate=1e-5)
    for _ in range(130):
        ft.add_experience({"a": 1}, {"b": 2}, {"c": 3}, {"d": 4})
    assert len(ft._buffer) == 130
    assert ft._buffer[-1] == {"obs": {"a": 1}, "action": {"b": 2}, "reward": {"c": 3}, "next_obs": {"d": 4}}


@pytest.mark.asyncio
async def test_online_finetuner_step_insufficient():
    ft = OnlineFinetuner(controller=None)
    for _ in range(100):  # fewer than 128
        ft.add_experience({"x": 0}, {"y": 0}, {"r": 0}, {"nx": 0})
    result = await ft.finetune_step()
    assert result is None


@pytest.mark.asyncio
async def test_online_finetuner_step_sufficient():
    ft = OnlineFinetuner(controller=None)
    for _ in range(200):
        ft.add_experience({"x": 0}, {"y": 0}, {"r": 0}, {"nx": 0})
    result = await ft.finetune_step()
    assert result is not None
    assert result["samples"] == 128


def test_online_finetuner_buffer_cap():
    ft = OnlineFinetuner(controller=None)
    ft._max_buffer = 100
    for i in range(150):
        ft.add_experience({"i": i}, {}, {}, {})
    assert len(ft._buffer) == 100
    assert ft._buffer[0]["obs"]["i"] == 50  # first 50 dropped
    assert ft._buffer[-1]["obs"]["i"] == 149


@pytest.mark.asyncio
async def test_auto_trainer_lifecycle():
    from agent_service.rl.training.auto_trainer import AutoTrainer

    trainer = AutoTrainer(controller=None, session_factory=None, redis=None, train_interval_hours=999)
    await trainer.start()
    assert trainer._task is not None
    assert not trainer._task.done()
    await trainer.stop()
    # Wait a tick for cancellation to propagate
    await asyncio.sleep(0.05)
    assert trainer._task.cancelled() or trainer._task.done()
