import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class HealthScore(Base):
    __tablename__ = "health_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    overall_score = Column(Float, nullable=False)
    component_scores = Column(JSON, nullable=True)
    trend_direction = Column(String(8), nullable=True)  # up / down / stable
    trend_slope = Column(Float, nullable=True)


class RULPrediction(Base):
    __tablename__ = "rul_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    component = Column(String(64), nullable=False)
    predicted_hours = Column(Float, nullable=False)
    confidence_interval = Column(JSON, nullable=True)
    model_version = Column(String(32), nullable=True)
    degradation_model = Column(String(32), nullable=False)  # linear / exp / weibull
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class FaultDiagnosis(Base):
    __tablename__ = "fault_diagnoses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    symptom_signature = Column(JSON, nullable=False)
    matched_fmea_id = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=False)
    root_cause = Column(String(256), nullable=True)
    severity = Column(Integer, nullable=False)  # 1-5
    cert_level = Column(Integer, nullable=True)  # 1-4 per GB/T 23718


class FMEARecord(Base):
    __tablename__ = "fmea_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_type = Column(String(64), nullable=False)
    component = Column(String(64), nullable=False)
    failure_mode = Column(String(128), nullable=False)
    effects = Column(Text, nullable=True)
    severity = Column(Integer, nullable=False)
    occurrence = Column(Integer, nullable=False)
    detection = Column(Integer, nullable=False)
    rpn = Column(Integer, nullable=False)
    mitigation = Column(Text, nullable=True)
    symptoms = Column(JSON, nullable=True)


class VibrationSpectrum(Base):
    __tablename__ = "vibration_spectra"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    sample_rate = Column(Integer, nullable=True)
    fft_bins = Column(JSON, nullable=True)
    peak_frequencies = Column(JSON, nullable=True)
    bearing_fault_freqs = Column(JSON, nullable=True)
    crest_factor = Column(Float, nullable=True)
    vibration_zone = Column(String(2), nullable=True)  # A / B / C / D per GB/T 6075


class OilAnalysis(Base):
    __tablename__ = "oil_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    sample_date = Column(DateTime, nullable=False)
    viscosity = Column(Float, nullable=True)
    tan = Column(Float, nullable=True)  # total acid number
    moisture_ppm = Column(Float, nullable=True)
    wear_metals = Column(JSON, nullable=True)
    particle_count_iso = Column(String(16), nullable=True)


class ModelValidation(Base):
    __tablename__ = "model_validations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, nullable=False)
    actual_outcome = Column(JSON, nullable=True)
    accuracy = Column(Float, nullable=True)
    feedback_source = Column(String(32), nullable=True)  # workorder / inspection
    retrained = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
