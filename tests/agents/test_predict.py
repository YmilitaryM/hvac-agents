import pytest
import numpy as np
from src.agents.predict import predict_load, LoadForecast, PredictAgent


class TestLoadForecast:
    def test_forecast_dataclass(self):
        f = LoadForecast(
            timestamp=1716000000.0,
            load_15min=450.0, load_1h=450.0,
            load_6h=420.0, load_24h=400.0,
            confidence_15min=0.95, confidence_1h=0.90,
            confidence_6h=0.70, confidence_24h=0.55,
            outdoor_temp=32.0, outdoor_humidity=60.0,
        )
        assert f.load_15min == 450.0
        assert f.confidence_24h == 0.55


class TestPredictLoad:
    def test_hot_day_high_load(self):
        result = predict_load(
            outdoor_temp=35.0, outdoor_humidity=60.0,
            hour_of_day=14, day_of_week=2,
        )
        # 35C - 18 = 17 * 50 = 850 base * ~1.1 humidity * ~1.3 time = high
        assert result.load_15min > 500
        assert result.load_1h > 500

    def test_cool_day_low_load(self):
        result = predict_load(
            outdoor_temp=20.0, outdoor_humidity=40.0,
            hour_of_day=14, day_of_week=2,
        )
        assert result.load_15min < 300

    def test_below_balance_point_zero_base(self):
        result = predict_load(
            outdoor_temp=15.0, outdoor_humidity=50.0,
            hour_of_day=10, day_of_week=2,
        )
        # Below 18C, base should be near 0
        assert result.load_15min >= 0
        assert result.load_15min < 100  # nearly zero, just small residual

    def test_nighttime_lower_than_daytime(self):
        day = predict_load(
            outdoor_temp=30.0, outdoor_humidity=50.0,
            hour_of_day=14, day_of_week=2,
        )
        night = predict_load(
            outdoor_temp=30.0, outdoor_humidity=50.0,
            hour_of_day=4, day_of_week=2,
        )
        assert night.load_15min < day.load_15min

    def test_weekend_lower_than_weekday(self):
        weekday = predict_load(
            outdoor_temp=30.0, outdoor_humidity=50.0,
            hour_of_day=14, day_of_week=2,  # Tuesday
        )
        weekend = predict_load(
            outdoor_temp=30.0, outdoor_humidity=50.0,
            hour_of_day=14, day_of_week=6,  # Saturday
        )
        assert weekend.load_15min < weekday.load_15min

    def test_humidity_increases_load(self):
        dry = predict_load(
            outdoor_temp=30.0, outdoor_humidity=30.0,
            hour_of_day=14, day_of_week=2,
        )
        humid = predict_load(
            outdoor_temp=30.0, outdoor_humidity=80.0,
            hour_of_day=14, day_of_week=2,
        )
        assert humid.load_15min > dry.load_15min

    def test_confidence_decreases_with_horizon(self):
        result = predict_load(
            outdoor_temp=30.0, outdoor_humidity=50.0,
            hour_of_day=14, day_of_week=2,
        )
        assert result.confidence_15min > result.confidence_1h
        assert result.confidence_1h > result.confidence_6h
        assert result.confidence_6h > result.confidence_24h

    def test_longer_horizons_have_wider_range(self):
        result = predict_load(
            outdoor_temp=30.0, outdoor_humidity=50.0,
            hour_of_day=14, day_of_week=2,
        )
        # 6h and 24h should differ from 15min (scaled down)
        assert result.load_6h != result.load_15min or result.load_24h != result.load_15min

    def test_historical_load_blending(self):
        no_hist = predict_load(
            outdoor_temp=30.0, outdoor_humidity=50.0,
            hour_of_day=14, day_of_week=2,
        )
        with_hist = predict_load(
            outdoor_temp=30.0, outdoor_humidity=50.0,
            hour_of_day=14, day_of_week=2,
            historical_load=[600, 620, 610, 590, 605],
        )
        # With history, result should be pulled toward historical average
        assert with_hist.load_15min != no_hist.load_15min

    def test_returns_positive_values(self):
        result = predict_load(
            outdoor_temp=40.0, outdoor_humidity=90.0,
            hour_of_day=14, day_of_week=2,
        )
        assert result.load_15min > 0
        assert result.load_1h > 0
        assert result.load_6h > 0
        assert result.load_24h > 0


class TestPredictAgent:
    @pytest.mark.asyncio
    async def test_run_uses_predict_load(self):
        agent = PredictAgent()
        result = await agent.run({
            "outdoor_temp": 32.0,
            "outdoor_humidity": 55.0,
            "hour_of_day": 14,
            "day_of_week": 2,
        })
        assert "load_forecast" in result
        fc = result["load_forecast"]
        assert fc["load_15min"] > 0
        assert fc["confidence_15min"] > 0.9
        assert "predictions" in result  # multi-horizon dict
