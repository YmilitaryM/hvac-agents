# services/energy/energy_service/models.py
import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Multi-tenant data isolation
# ---------------------------------------------------------------------------
# Every model below MUST include a tenant_id column so that each tenant's
# data is isolated.  The gateway forwards ``X-Tenant-Id`` and the
# TenantMiddleware (already added in main.py) sets the ContextVar.
#
# To apply tenant filtering in queries use the helper from common.tenant:
#
#     from common.tenant import tenant_filter
#     q = select(EnergySnapshot).where(...)
#     q = tenant_filter(q, EnergySnapshot)
#
# For models not yet migrated, the tenant_filter will silently pass through
# (no filter applied) since the column doesn't exist.
# ---------------------------------------------------------------------------


class EnergySnapshot(Base):
    __tablename__ = "energy_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True, default=1,
    )
    plant_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    total_power_kw = Column(Float, nullable=False)
    cop = Column(Float, nullable=False)
    cooling_load_rt = Column(Float, nullable=False)
    equipment_power_breakdown = Column(JSON, nullable=True)
    outdoor_wb_temp = Column(Float, nullable=True)


class EnergyPrice(Base):
    __tablename__ = "energy_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    price_per_kwh = Column(Float, nullable=False)
    period = Column(String(16), nullable=False)  # peak / valley / flat
    carbon_intensity = Column(Float, nullable=True)


class EnergyBaseline(Base):
    __tablename__ = "energy_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    baseline_kwh_per_rt = Column(Float, nullable=False)
    method = Column(String(32), nullable=False)  # regression / simple
    r_squared = Column(Float, nullable=True)
    climate_zone = Column(String(8), nullable=True)
    building_type = Column(String(32), nullable=True)


class DemandEvent(Base):
    __tablename__ = "demand_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    peak_kw = Column(Float, nullable=False)
    target_kw = Column(Float, nullable=False)
    strategy = Column(String(32), nullable=False)  # load_shift / shed / storage
    actual_reduction_kw = Column(Float, nullable=True)


class EnergyReport(Base):
    __tablename__ = "energy_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, nullable=False, index=True)
    period = Column(String(16), nullable=False)  # day / week / month / year
    report_type = Column(String(32), nullable=False)  # daily / audit / certificate
    summary = Column(JSON, nullable=True)
    file_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PowerQuality(Base):
    __tablename__ = "power_quality"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    thd_v_pct = Column(Float, nullable=True)
    thd_i_pct = Column(Float, nullable=True)
    power_factor = Column(Float, nullable=True)
    voltage_unbalance_pct = Column(Float, nullable=True)
    frequency_hz = Column(Float, nullable=True)
