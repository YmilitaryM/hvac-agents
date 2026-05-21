def test_peak_valley_scheduler_basic():
    from services.agent.agent_service.energy.scheduler import schedule_peak_valley
    forecast_load = [200, 220, 250, 280, 300, 310, 290, 260, 240, 220, 200, 180,
                     170, 160, 150, 180, 220, 280, 320, 350, 360, 340, 300, 260]
    price_period = ["flat"] * 8 + ["peak"] * 4 + ["flat"] * 4 + ["peak"] * 4 + ["valley"] * 4
    result = schedule_peak_valley(forecast_load, price_period)
    assert "chiller_plan" in result
    assert "expected_savings" in result
    assert result["expected_savings"] >= 0


def test_baseline_engine_fit():
    from services.agent.agent_service.energy.baseline_engine import fit_baseline
    load_rt = [100, 150, 200, 250, 300, 350, 400, 100, 150, 200, 250, 300]
    energy_kwh = [120, 170, 220, 270, 320, 370, 420, 115, 165, 215, 265, 315]
    result = fit_baseline(load_rt, energy_kwh)
    assert "baseline_kwh_per_rt" in result
    assert "r_squared" in result
    assert result["r_squared"] > 0.8


def test_demand_predictor_warns_above_limit():
    from services.agent.agent_service.energy.demand_predictor import predict_demand
    power_history = [400, 420, 440, 460, 480, 500, 490, 470, 450, 430]
    result = predict_demand(power_history, demand_limit=480)
    assert "predicted_peak" in result
    assert "warning" in result
    if result["predicted_peak"] > 480:
        assert result["warning"] is True


def test_mv_verifier_computes_savings():
    from services.agent.agent_service.energy.mv_verifier import verify_savings
    result = verify_savings(baseline_kwh=120000, actual_kwh=108000)
    assert result["savings_kwh"] == 12000
    assert result["savings_pct"] == 10.0
    assert result["carbon_reduction_kg"] > 0
