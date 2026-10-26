"""Pydantic response models for the public API."""

from datetime import date

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str


class OverviewResponse(BaseModel):
    production_quantity: int
    production_target: int
    target_attainment_pct: float | None
    oee_pct: float | None
    unplanned_downtime_minutes: float
    inspected_units: int
    defective_units: int
    defect_rate_pct: float | None


class ProductionTrendResponse(BaseModel):
    production_date: date
    production_quantity: int
    good_quantity: int
    production_target: int


class ProductionLineResponse(BaseModel):
    line_id: int
    line_code: str
    line_name: str
    factory_name: str
    production_quantity: int
    production_target: int
    target_attainment_pct: float | None
    unplanned_downtime_minutes: float


class DowntimeCauseResponse(BaseModel):
    cause: str
    is_planned: bool
    event_count: int
    downtime_minutes: float


class DowntimeMachineResponse(BaseModel):
    downtime_rank: int
    machine_id: int
    machine_code: str
    machine_name: str
    production_line: str
    factory_name: str
    unplanned_event_count: int
    unplanned_downtime_minutes: float


class QualityLineResponse(BaseModel):
    line_id: int
    line_code: str
    line_name: str
    factory_name: str
    inspected_units: int
    defective_units: int
    defect_rate_pct: float | None


class MachineResponse(BaseModel):
    machine_id: int
    machine_code: str
    machine_name: str
    machine_type: str
    rated_capacity_per_hour: float
    line_id: int
    line_code: str
    line_name: str
    factory_id: int
    factory_name: str
    production_quantity: int
    production_target: int
    target_attainment_pct: float | None
    unplanned_downtime_minutes: float
    inspected_units: int
    defective_units: int
    defect_rate_pct: float | None
