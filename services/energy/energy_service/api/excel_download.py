"""Excel download endpoints for the energy service."""

from fastapi import APIRouter, Query
from fastapi.responses import Response

from ..excel_generator import (
    generate_comparison_excel,
    generate_energy_report_excel,
    generate_mv_excel,
)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

router = APIRouter()


@router.get("/reports/download")
async def download_reports(plant_id: int = Query(...), period: str = "month"):
    """Download energy report list as Excel file."""
    # Use the same demo data as the reports endpoint
    data = {
        "items": [
            {"id": 1, "period": "day", "report_type": "daily", "created_at": "2026-05-20T08:00:00"},
            {"id": 2, "period": "month", "report_type": "audit", "created_at": "2026-05-01T08:00:00"},
        ],
    }
    excel_bytes = generate_energy_report_excel(period, data)
    return Response(
        content=excel_bytes,
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename=energy_report_{period}.xlsx"},
    )


@router.get("/mv/download")
async def download_mv(plant_id: int = Query(...)):
    """Download M&V verification results as Excel file."""
    # Use the same demo data as the MV verify endpoint
    data = {
        "plant_id": plant_id,
        "baseline_energy_kwh": 120000.0,
        "actual_energy_kwh": 108000.0,
        "savings_kwh": 12000.0,
        "savings_pct": 10.0,
        "uncertainty_pct": 8.5,
        "cv_rmse_pct": 15.2,
        "nmbe_pct": -1.8,
        "compliant_ashrae_g14": True,
        "compliant_gb28750": True,
        "coal_equivalent_tons": 4.8,
        "carbon_reduction_kg": 9600.0,
    }
    excel_bytes = generate_mv_excel(data)
    return Response(
        content=excel_bytes,
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename=mv_verification_plant{plant_id}.xlsx"},
    )


@router.get("/comparison/download")
async def download_comparison(plant_id: int = Query(...), period: str = "month"):
    """Download energy comparison report as Excel file."""
    # Use the same demo data as the comparison endpoint
    data = {
        "plant_id": plant_id,
        "period": period,
        "current": {"total_kwh": 108000, "avg_cop": 5.2, "avg_power_kw": 450},
        "previous": {"total_kwh": 112000, "avg_cop": 5.0, "avg_power_kw": 467},
        "mom_change_pct": {"total_kwh": -3.6, "avg_cop": 4.0, "avg_power_kw": -3.6},
        "yoy_change_pct": {"total_kwh": -5.2, "avg_cop": 6.1, "avg_power_kw": -5.2},
    }
    excel_bytes = generate_comparison_excel(data)
    return Response(
        content=excel_bytes,
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename=energy_comparison_{period}_{plant_id}.xlsx"},
    )
