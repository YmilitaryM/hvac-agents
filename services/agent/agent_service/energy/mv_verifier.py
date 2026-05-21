def verify_savings(baseline_kwh: float, actual_kwh: float, carbon_factor: float = 0.8) -> dict:
    """
    Verify energy savings per ASHRAE Guideline 14 and GB/T 28750 + GB/T 13234.
    carbon_factor: kg CO2 per kWh (default 0.8 for China grid average)
    """
    savings_kwh = baseline_kwh - actual_kwh
    savings_pct = (savings_kwh / baseline_kwh * 100) if baseline_kwh > 0 else 0
    coal_equivalent = savings_kwh * 0.0004
    carbon_reduction = savings_kwh * carbon_factor

    return {
        "baseline_kwh": baseline_kwh,
        "actual_kwh": actual_kwh,
        "savings_kwh": round(savings_kwh, 1),
        "savings_pct": round(savings_pct, 1),
        "coal_equivalent_tons": round(coal_equivalent, 2),
        "carbon_reduction_kg": round(carbon_reduction, 1),
        "compliant_gb28750": abs(savings_pct) <= 50,
    }
