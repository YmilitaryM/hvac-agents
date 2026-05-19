import uuid

from sqlalchemy import Column, String, Float, Integer

from common.db import Base


class WeatherRecordModel(Base):
    __tablename__ = "weather_records"
    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    timestamp = Column(Float, primary_key=True, index=True)
    outdoor_db_temp = Column(Float)
    outdoor_wb_temp = Column(Float)
    relative_humidity = Column(Float)
    solar_radiation_wm2 = Column(Float, default=0)
    wind_speed_ms = Column(Float, default=0)
    wind_direction = Column(Float, default=0)
    cloud_cover = Column(Float, default=0)


class EnergyPriceModel(Base):
    __tablename__ = "energy_prices"
    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    timestamp = Column(Float, primary_key=True, index=True)
    electricity_price_per_kwh = Column(Float)
    carbon_intensity_kg_per_kwh = Column(Float, default=0.0)


class BuildingModel(Base):
    __tablename__ = "buildings"
    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    name = Column(String(128))
    area_m2 = Column(Float)
    floor_count = Column(Integer, default=1)
    orientation = Column(String(16), default="south")
    window_wall_ratio = Column(Float, default=0.3)
    wall_u_value = Column(Float, default=1.5)
    roof_u_value = Column(Float, default=0.8)
    glass_shgc = Column(Float, default=0.6)
    building_type = Column(String(32), default="office")
