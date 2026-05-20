"""Unit tests for Equipment Pydantic schemas, enums, and schema conversion logic."""

import pytest
from datetime import datetime, timezone

from common.schemas.equipment import (
    EquipmentSchema,
    EquipmentPointSchema,
    EquipmentTypeSchema,
    PointTemplateSchema,
    IODirection,
    EquipmentCategory,
)


# ── IODirection enum ──────────────────────────────────────────────────

class TestIODirection:
    def test_members(self):
        assert IODirection.INPUT.value == "input"
        assert IODirection.CALC.value == "calc"
        assert IODirection.OUTPUT.value == "output"

    def test_member_count(self):
        assert len(IODirection) == 3

    def test_str_enum_comparison(self):
        """StrEnum values compare equal to their string values."""
        assert IODirection.INPUT == "input"
        assert IODirection.OUTPUT == "output"
        assert IODirection.CALC == "calc"

    def test_str_enum_value_attribute(self):
        """The .value attribute of a StrEnum member is the string."""
        assert IODirection.INPUT.value == "input"
        assert IODirection.OUTPUT.value == "output"


# ── EquipmentCategory enum ────────────────────────────────────────────

class TestEquipmentCategory:
    VALID_CATEGORIES = {"chiller", "pump", "cooling_tower", "valve", "pipe", "sensor"}

    def test_members(self):
        assert EquipmentCategory.CHILLER.value == "chiller"
        assert EquipmentCategory.PUMP.value == "pump"
        assert EquipmentCategory.COOLING_TOWER.value == "cooling_tower"
        assert EquipmentCategory.VALVE.value == "valve"
        assert EquipmentCategory.PIPE.value == "pipe"
        assert EquipmentCategory.SENSOR.value == "sensor"

    def test_member_count(self):
        assert len(EquipmentCategory) == 6

    def test_all_categories_covered(self):
        actual = {m.value for m in EquipmentCategory}
        assert actual == self.VALID_CATEGORIES


# ── EquipmentPointSchema ──────────────────────────────────────────────

class TestEquipmentPointSchema:
    def test_minimal_valid_input(self):
        pt = EquipmentPointSchema(
            id="pt1",
            equipment_id="eq1",
            point_template_id="tmpl1",
            code="CHWST",
            name="Chilled Water Supply Temp",
            unit="degC",
            io_direction="input",
        )
        assert pt.id == "pt1"
        assert pt.unit == "degC"
        assert pt.io_direction == IODirection.INPUT
        assert pt.current_value is None
        assert pt.last_updated is None

    def test_missing_required_field_raises(self):
        with pytest.raises(ValueError):
            EquipmentPointSchema(
                id="pt1",
                equipment_id="eq1",
                point_template_id="tmpl1",
                code="CHWST",
                # name is required and missing
                unit="degC",
                io_direction="input",
            )

    def test_invalid_io_direction_raises(self):
        with pytest.raises(ValueError):
            EquipmentPointSchema(
                id="pt1",
                equipment_id="eq1",
                point_template_id="tmpl1",
                code="CHWST",
                name="Temp",
                unit="degC",
                io_direction="not_valid",
            )

    def test_optional_fields_default(self):
        pt = EquipmentPointSchema(
            id="pt1",
            equipment_id="eq1",
            point_template_id="tmpl1",
            code="CHWST",
            name="Temp",
            unit="degC",
            io_direction="output",
        )
        assert pt.current_value is None
        assert pt.last_updated is None

    def test_current_value_accepts_float(self):
        pt = EquipmentPointSchema(
            id="pt1",
            equipment_id="eq1",
            point_template_id="tmpl1",
            code="CHWST",
            name="Temp",
            unit="degC",
            io_direction="input",
            current_value=12.5,
            last_updated=1716210000.0,
        )
        assert pt.current_value == 12.5
        assert pt.last_updated == 1716210000.0


# ── EquipmentSchema ───────────────────────────────────────────────────

class TestEquipmentSchema:
    def test_minimal_valid(self):
        eq = EquipmentSchema(
            id="eq1",
            name="Chiller-01",
            equipment_type_id="et1",
        )
        assert eq.id == "eq1"
        assert eq.name == "Chiller-01"
        assert eq.plant_id is None
        assert eq.design_params == {}
        assert eq.is_active is True
        assert eq.points == []
        assert eq.created_at is None

    def test_missing_name_raises(self):
        with pytest.raises(ValueError):
            EquipmentSchema(
                id="eq1",
                equipment_type_id="et1",
            )

    def test_missing_equipment_type_id_raises(self):
        with pytest.raises(ValueError):
            EquipmentSchema(
                id="eq1",
                name="Chiller-01",
            )

    def test_with_plant_and_design_params(self):
        eq = EquipmentSchema(
            id="eq2",
            name="Pump-01",
            equipment_type_id="et2",
            plant_id="plant1",
            design_params={"rated_flow": 100, "rated_head": 30},
        )
        assert eq.plant_id == "plant1"
        assert eq.design_params["rated_flow"] == 100

    def test_with_points(self):
        pts = [
            EquipmentPointSchema(
                id="p1",
                equipment_id="eq1",
                point_template_id="t1",
                code="CHWST",
                name="Supply Temp",
                unit="degC",
                io_direction="input",
                current_value=7.0,
            ),
            EquipmentPointSchema(
                id="p2",
                equipment_id="eq1",
                point_template_id="t2",
                code="CHWRT",
                name="Return Temp",
                unit="degC",
                io_direction="input",
                current_value=12.0,
            ),
        ]
        eq = EquipmentSchema(
            id="eq1",
            name="Chiller-01",
            equipment_type_id="et1",
            points=pts,
        )
        assert len(eq.points) == 2
        assert eq.points[0].code == "CHWST"
        assert eq.points[0].current_value == 7.0

    def test_is_active_defaults_true(self):
        eq = EquipmentSchema(
            id="eq1",
            name="Chiller-01",
            equipment_type_id="et1",
        )
        assert eq.is_active is True

    def test_is_active_false(self):
        eq = EquipmentSchema(
            id="eq1",
            name="Chiller-01",
            equipment_type_id="et1",
            is_active=False,
        )
        assert eq.is_active is False

    def test_design_params_defaults_empty_dict(self):
        eq = EquipmentSchema(
            id="eq1",
            name="Chiller-01",
            equipment_type_id="et1",
        )
        assert eq.design_params == {}

    def test_created_at_accepts_datetime(self):
        now = datetime.now(timezone.utc)
        eq = EquipmentSchema(
            id="eq1",
            name="Chiller-01",
            equipment_type_id="et1",
            created_at=now,
        )
        assert eq.created_at == now


# ── PointTemplateSchema ───────────────────────────────────────────────

class TestPointTemplateSchema:
    def test_minimal_valid(self):
        tmpl = PointTemplateSchema(
            id="t1",
            code="CHWST",
            name="Supply Temp",
            io_direction="input",
        )
        assert tmpl.unit == ""
        assert tmpl.data_type == "float"
        assert tmpl.required is False
        assert tmpl.sort_order == 0

    def test_io_direction_enum_coercion(self):
        tmpl = PointTemplateSchema(
            id="t1",
            code="CHWST",
            name="Supply Temp",
            io_direction="output",
        )
        assert tmpl.io_direction == IODirection.OUTPUT

    def test_required_flag(self):
        tmpl = PointTemplateSchema(
            id="t1",
            code="CHWST",
            name="Supply Temp",
            io_direction="input",
            required=True,
        )
        assert tmpl.required is True


# ── EquipmentTypeSchema ───────────────────────────────────────────────

class TestEquipmentTypeSchema:
    def test_valid_chiller_type(self):
        pts = [
            PointTemplateSchema(
                id="pt1", code="CHWST", name="Supply Temp", io_direction="input",
            ),
            PointTemplateSchema(
                id="pt2", code="CHWRT", name="Return Temp", io_direction="input",
            ),
        ]
        et = EquipmentTypeSchema(
            id="et1",
            type_code="centrifugal_chiller",
            type_name="Centrifugal Chiller",
            category="chiller",
            points=pts,
        )
        assert et.type_code == "centrifugal_chiller"
        assert et.category == EquipmentCategory.CHILLER
        assert len(et.points) == 2

    def test_category_coercion(self):
        et = EquipmentTypeSchema(
            id="et1",
            type_code="cooling_tower_open",
            type_name="Cooling Tower",
            category="cooling_tower",
        )
        assert et.category == EquipmentCategory.COOLING_TOWER

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError):
            EquipmentTypeSchema(
                id="et1",
                type_code="unknown",
                type_name="Unknown",
                category="not_a_valid_category",
            )

    def test_missing_type_code_raises(self):
        with pytest.raises(ValueError):
            EquipmentTypeSchema(
                id="et1",
                type_name="Chiller",
                category="chiller",
            )

    def test_empty_points_default(self):
        et = EquipmentTypeSchema(
            id="et1",
            type_code="sensor_temp",
            type_name="Temperature Sensor",
            category="sensor",
        )
        assert et.points == []
