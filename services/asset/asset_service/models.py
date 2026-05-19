import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Float, Integer, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db import Base


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EquipmentTypeModel(Base):
    __tablename__ = "equipment_types"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    type_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    type_name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    points: Mapped[list["PointTemplateModel"]] = relationship(back_populates="equipment_type", cascade="all, delete-orphan")


class PointTemplateModel(Base):
    __tablename__ = "point_templates"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    equipment_type_id: Mapped[str] = mapped_column(String(32), ForeignKey("equipment_types.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    unit: Mapped[str] = mapped_column(String(32), default="")
    data_type: Mapped[str] = mapped_column(String(32), default="float")
    io_direction: Mapped[str] = mapped_column(String(16))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    equipment_type: Mapped[EquipmentTypeModel] = relationship(back_populates="points")


class EquipmentModel(Base):
    __tablename__ = "equipment"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(128), index=True)
    equipment_type_id: Mapped[str] = mapped_column(String(32), ForeignKey("equipment_types.id"))
    plant_id: Mapped[Optional[str]] = mapped_column(String(32), ForeignKey("plants.id"), nullable=True, index=True)
    design_params: Mapped[dict] = mapped_column(JSON, default=dict)
    position_x: Mapped[float] = mapped_column(Float, default=0)
    position_y: Mapped[float] = mapped_column(Float, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    points: Mapped[list["EquipmentPointModel"]] = relationship(back_populates="equipment", cascade="all, delete-orphan")


class EquipmentPointModel(Base):
    __tablename__ = "equipment_points"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    equipment_id: Mapped[str] = mapped_column(String(32), ForeignKey("equipment.id"), index=True)
    point_template_id: Mapped[str] = mapped_column(String(32), ForeignKey("point_templates.id"))
    custom_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    current_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_updated: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    protocol_binding: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    equipment: Mapped[EquipmentModel] = relationship(back_populates="points")


class PlantModel(Base):
    __tablename__ = "plants"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    site_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    data_source_mode: Mapped[str] = mapped_column(String(16), default="simulated")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    loops: Mapped[list["LoopModel"]] = relationship(back_populates="plant", cascade="all, delete-orphan")
    equipment: Mapped[list[EquipmentModel]] = relationship(back_populates="plant", foreign_keys="EquipmentModel.plant_id")


class LoopModel(Base):
    __tablename__ = "loops"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    plant_id: Mapped[str] = mapped_column(String(32), ForeignKey("plants.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    fluid_type: Mapped[str] = mapped_column(String(32))
    loop_type: Mapped[str] = mapped_column(String(32), default="primary")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    plant: Mapped[PlantModel] = relationship(back_populates="loops")
    pipe_segments: Mapped[list["PipeSegmentModel"]] = relationship(back_populates="loop", cascade="all, delete-orphan")


class PipeSegmentModel(Base):
    __tablename__ = "pipe_segments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    loop_id: Mapped[str] = mapped_column(String(32), ForeignKey("loops.id"), index=True)
    from_point_id: Mapped[str] = mapped_column(String(32), ForeignKey("equipment_points.id"))
    to_point_id: Mapped[str] = mapped_column(String(32), ForeignKey("equipment_points.id"))
    diameter_mm: Mapped[float] = mapped_column(Float, default=200)
    length_m: Mapped[float] = mapped_column(Float, default=5.0)
    roughness_mm: Mapped[float] = mapped_column(Float, default=0.045)
    insulation_type: Mapped[str] = mapped_column(String(32), default="none")
    valve_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    loop: Mapped[LoopModel] = relationship(back_populates="pipe_segments")
