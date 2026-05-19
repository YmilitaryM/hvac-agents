import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import numpy as np

from .agents.base import BaseAgent


@dataclass
class LoadForecast:
    """Multi-timescale load forecast result."""
    timestamp: float
    load_15min: float   # RT (refrigeration tons)
    load_1h: float
    load_6h: float
    load_24h: float
    confidence_15min: float   # 0-1
    confidence_1h: float
    confidence_6h: float
    confidence_24h: float
    outdoor_temp: float
    outdoor_humidity: float
    method: str = "regression"


def predict_load(
    outdoor_temp: float,
    outdoor_humidity: float,
    hour_of_day: int,
    day_of_week: int,
    historical_load: Optional[List[float]] = None,
) -> LoadForecast:
    """Predict cooling load using a simplified regression model.

    Cooling load is driven primarily by outdoor temperature (sensible heat)
    and humidity (latent heat), modulated by time-of-day and day-of-week patterns.

    Returns a LoadForecast with predictions at 15min, 1h, 6h, 24h horizons
    and decreasing confidence for longer horizons.
    """
    # 1. Base load from outdoor temp (balance point at 18 deg C)
    #    50 RT per deg C above balance point
    base_load = max(0.0, (outdoor_temp - 18.0) * 50.0)

    # 2. Humidity correction: +1% load per %RH above 50%
    humidity_factor = 1.0 + max(0.0, outdoor_humidity - 50.0) * 0.01

    # 3. Time-of-day factor: sinusoidal, peak at 14:00 (1.3), trough near 4:00 (~0.4)
    #    sin(pi/12 * (h - 8)) gives peak at h=14, trough at h=2
    hour_angle = np.pi / 12.0 * (hour_of_day - 8.0)
    time_factor = 0.85 + 0.45 * np.sin(hour_angle)

    # 4. Day-of-week factor: weekday=1.0, weekend=0.7
    #    day_of_week: 0=Monday ... 6=Sunday
    is_weekend = day_of_week >= 5
    dow_factor = 0.7 if is_weekend else 1.0

    # Combine factors to get predicted load
    predicted = base_load * humidity_factor * time_factor * dow_factor

    # 5. Historical smoothing: blend with exponential weighted average (alpha=0.3)
    if historical_load and len(historical_load) > 0:
        hist_avg = float(np.mean(historical_load))
        alpha = 0.3
        predicted = alpha * hist_avg + (1.0 - alpha) * predicted

    # 6. Multi-horizon scaling (weather uncertainty increases with horizon)
    load_15min = float(predicted)
    load_1h = float(predicted)
    load_6h = float(predicted * 0.90)
    load_24h = float(predicted * 0.85)

    # 7. Confidence decreases with horizon
    confidence_15min = 0.95
    confidence_1h = 0.90
    confidence_6h = 0.70
    confidence_24h = 0.55

    return LoadForecast(
        timestamp=float(time.time()),
        load_15min=load_15min,
        load_1h=load_1h,
        load_6h=load_6h,
        load_24h=load_24h,
        confidence_15min=confidence_15min,
        confidence_1h=confidence_1h,
        confidence_6h=confidence_6h,
        confidence_24h=confidence_24h,
        outdoor_temp=outdoor_temp,
        outdoor_humidity=outdoor_humidity,
        method="regression",
    )


class PredictAgent(BaseAgent):
    """Predict Agent -- forecasts cooling load at multiple time horizons."""

    def __init__(self, llm=None, context=None):
        super().__init__(name="predict", llm=llm, context=context)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run load prediction using the regression model.

        Args:
            input_data: Must contain outdoor_temp, outdoor_humidity,
                        hour_of_day, day_of_week.
                        May optionally contain historical_load.

        Returns:
            Dict with load_forecast (as dict) and predictions (multi-horizon dict).
        """
        outdoor_temp = float(input_data["outdoor_temp"])
        outdoor_humidity = float(input_data["outdoor_humidity"])
        hour_of_day = int(input_data["hour_of_day"])
        day_of_week = int(input_data["day_of_week"])
        historical_load = input_data.get("historical_load", None)

        forecast = predict_load(
            outdoor_temp=outdoor_temp,
            outdoor_humidity=outdoor_humidity,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            historical_load=historical_load,
        )

        return {
            "load_forecast": {
                "timestamp": forecast.timestamp,
                "load_15min": forecast.load_15min,
                "load_1h": forecast.load_1h,
                "load_6h": forecast.load_6h,
                "load_24h": forecast.load_24h,
                "confidence_15min": forecast.confidence_15min,
                "confidence_1h": forecast.confidence_1h,
                "confidence_6h": forecast.confidence_6h,
                "confidence_24h": forecast.confidence_24h,
                "outdoor_temp": forecast.outdoor_temp,
                "outdoor_humidity": forecast.outdoor_humidity,
                "method": forecast.method,
            },
            "predictions": {
                "15min": forecast.load_15min,
                "1h": forecast.load_1h,
                "6h": forecast.load_6h,
                "24h": forecast.load_24h,
            },
        }
