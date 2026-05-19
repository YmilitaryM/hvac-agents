from sqlalchemy import select
from .models import EquipmentTypeModel, PointTemplateModel


SEED_TYPES = [
    {
        "type_code": "centrifugal_chiller",
        "type_name": "离心式冷水主机",
        "category": "chiller",
        "points": [
            {"code": "chw_supply_temp", "name": "冷冻水供水温度", "unit": "°C", "io_direction": "input", "required": True, "sort_order": 1},
            {"code": "chw_return_temp", "name": "冷冻水回水温度", "unit": "°C", "io_direction": "input", "required": True, "sort_order": 2},
            {"code": "cw_entering_temp", "name": "冷却水进水温度", "unit": "°C", "io_direction": "input", "required": True, "sort_order": 3},
            {"code": "cw_leaving_temp", "name": "冷却水出水温度", "unit": "°C", "io_direction": "calc", "required": True, "sort_order": 4},
            {"code": "power_kw", "name": "实时功率", "unit": "kW", "io_direction": "calc", "required": True, "sort_order": 5},
            {"code": "current_load_rt", "name": "实时冷负荷", "unit": "RT", "io_direction": "calc", "required": True, "sort_order": 6},
            {"code": "evap_flow_rate", "name": "蒸发器流量", "unit": "L/s", "io_direction": "output", "sort_order": 7},
            {"code": "cond_flow_rate", "name": "冷凝器流量", "unit": "L/s", "io_direction": "output", "sort_order": 8},
            {"code": "run_status", "name": "运行状态", "unit": "enum", "data_type": "string", "io_direction": "output", "required": True, "sort_order": 9},
            {"code": "cumulative_hours", "name": "累计运行小时", "unit": "h", "io_direction": "output", "sort_order": 10},
        ]
    },
    {
        "type_code": "pump",
        "type_name": "水泵",
        "category": "pump",
        "points": [
            {"code": "speed_hz", "name": "运行频率", "unit": "Hz", "io_direction": "input", "required": True, "sort_order": 1},
            {"code": "power_kw", "name": "实时功率", "unit": "kW", "io_direction": "calc", "required": True, "sort_order": 2},
            {"code": "flow_lps", "name": "流量", "unit": "L/s", "io_direction": "calc", "required": True, "sort_order": 3},
            {"code": "inlet_pressure", "name": "进口压力", "unit": "kPa", "io_direction": "input", "sort_order": 4},
            {"code": "outlet_pressure", "name": "出口压力", "unit": "kPa", "io_direction": "calc", "sort_order": 5},
            {"code": "run_status", "name": "运行状态", "unit": "enum", "data_type": "string", "io_direction": "output", "required": True, "sort_order": 6},
        ]
    },
    {
        "type_code": "cooling_tower",
        "type_name": "冷却塔",
        "category": "cooling_tower",
        "points": [
            {"code": "fan_speed_hz", "name": "风机频率", "unit": "Hz", "io_direction": "input", "required": True, "sort_order": 1},
            {"code": "water_in_temp", "name": "进水温度", "unit": "°C", "io_direction": "input", "required": True, "sort_order": 2},
            {"code": "water_out_temp", "name": "出水温度", "unit": "°C", "io_direction": "calc", "required": True, "sort_order": 3},
            {"code": "water_flow_lps", "name": "水流量", "unit": "L/s", "io_direction": "input", "sort_order": 4},
            {"code": "fan_power_kw", "name": "风机功率", "unit": "kW", "io_direction": "calc", "sort_order": 5},
            {"code": "run_status", "name": "运行状态", "unit": "enum", "data_type": "string", "io_direction": "output", "required": True, "sort_order": 6},
        ]
    },
    {
        "type_code": "control_valve",
        "type_name": "电动调节阀",
        "category": "valve",
        "points": [
            {"code": "valve_position", "name": "阀门开度", "unit": "%", "io_direction": "input", "required": True, "sort_order": 1},
            {"code": "inlet_pressure", "name": "阀前压力", "unit": "kPa", "io_direction": "input", "required": True, "sort_order": 2},
            {"code": "outlet_pressure", "name": "阀后压力", "unit": "kPa", "io_direction": "calc", "required": True, "sort_order": 3},
            {"code": "flow_rate", "name": "通过流量", "unit": "L/s", "io_direction": "calc", "sort_order": 4},
            {"code": "actuator_status", "name": "执行器状态", "unit": "enum", "data_type": "string", "io_direction": "output", "sort_order": 5},
        ]
    },
    {
        "type_code": "temperature_sensor",
        "type_name": "温度传感器",
        "category": "sensor",
        "points": [
            {"code": "measured_temp", "name": "测量温度", "unit": "°C", "io_direction": "output", "required": True, "sort_order": 1},
        ]
    },
    {
        "type_code": "pressure_sensor",
        "type_name": "压力传感器",
        "category": "sensor",
        "points": [
            {"code": "measured_pressure", "name": "测量压力", "unit": "kPa", "io_direction": "output", "required": True, "sort_order": 1},
        ]
    },
    {
        "type_code": "flow_sensor",
        "type_name": "流量计",
        "category": "sensor",
        "points": [
            {"code": "measured_flow", "name": "测量流量", "unit": "L/s", "io_direction": "output", "required": True, "sort_order": 1},
        ]
    },
    {
        "type_code": "power_meter",
        "type_name": "功率计",
        "category": "sensor",
        "points": [
            {"code": "measured_power", "name": "测量功率", "unit": "kW", "io_direction": "output", "required": True, "sort_order": 1},
        ]
    },
]


async def seed_equipment_types(session_factory):
    async with session_factory() as session:
        for type_data in SEED_TYPES:
            existing = await session.execute(
                select(EquipmentTypeModel).where(EquipmentTypeModel.type_code == type_data["type_code"])
            )
            if existing.scalar_one_or_none():
                continue
            et = EquipmentTypeModel(
                type_code=type_data["type_code"],
                type_name=type_data["type_name"],
                category=type_data["category"],
            )
            session.add(et)
            await session.flush()
            for pt_data in type_data["points"]:
                pt = PointTemplateModel(equipment_type_id=et.id, **pt_data)
                session.add(pt)
        await session.commit()
