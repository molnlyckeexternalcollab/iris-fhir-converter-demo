"""
Pydantic models for Mock Integration Service

These models define the data structures for EHR/integration APIs.
FastAPI will auto-generate OpenAPI schemas from these models.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# HAC PI Risk Calculator Enums
# ============================================================================

class BradenMobilityScore(str, Enum):
    """Braden Scale Mobility assessment values."""
    COMPLETELY_IMMOBILE = "1"
    VERY_LIMITED = "2"
    SLIGHTLY_LIMITED = "3"
    NO_LIMITATION = "4"
    MISSING = "missing"


class BradenMoistureScore(str, Enum):
    """Braden Scale Moisture assessment values."""
    CONSTANTLY_MOIST = "1"
    VERY_MOIST = "2"
    OCCASIONALLY_MOIST = "3"
    RARELY_MOIST = "4"
    MISSING = "missing"


class BradenActivityScore(str, Enum):
    """Braden Scale Activity assessment values."""
    BEDFAST = "1"
    CHAIRFAST = "2"
    WALKS_OCCASIONALLY = "3"
    WALKS_FREQUENTLY = "4"
    MISSING = "missing"


class BradenFrictionScore(str, Enum):
    """Braden Scale Friction and Shear assessment values."""
    PROBLEM = "1"
    POTENTIAL_PROBLEM = "2"
    NO_APPARENT_PROBLEM = "3"
    MISSING = "missing"


class BradenSensoryScore(str, Enum):
    """Braden Scale Sensory Perception assessment values."""
    COMPLETELY_LIMITED = "1"
    VERY_LIMITED = "2"
    SLIGHTLY_LIMITED = "3"
    NO_IMPAIRMENT = "4"
    MISSING = "missing"


class GaitTransferScore(str, Enum):
    """Gait and Transfer assessment values."""
    NORMAL_GAIT = "0"
    WEAK_GAIT = "10"
    IMPAIRED_GAIT = "20"
    MISSING = "missing"


# ============================================================================
# Procedure Models
# ============================================================================

class Surgeon(BaseModel):
    """Surgeon information"""
    id: str = Field(..., description="Unique surgeon ID")
    name: str = Field(..., description="Surgeon full name")
    specialty: Optional[str] = Field(None, description="Medical specialty")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "SURG-001",
                "name": "Dr. Jane Smith",
                "specialty": "General Surgery"
            }
        }


class Procedure(BaseModel):
    """Scheduled surgical procedure from hospital EHR/integration system"""
    id: str = Field(..., description="Unique procedure ID")
    name: str = Field(..., description="Procedure name")
    cpt_code: str = Field(..., description="CPT (Current Procedural Terminology) code")
    scheduled_date: datetime = Field(..., description="Scheduled date and time")
    surgeon: Surgeon = Field(..., description="Assigned surgeon")
    patient_id: str = Field(..., description="Patient identifier (anonymized for POC)")
    room: Optional[str] = Field(None, description="Operating room assignment")
    estimated_duration_minutes: Optional[int] = Field(None, description="Estimated procedure duration", ge=0)
    status: str = Field(..., description="Procedure status (scheduled, in-progress, completed, cancelled)")
    notes: Optional[str] = Field(None, description="Additional procedure notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "PROC-456",
                "name": "Laparoscopic Cholecystectomy",
                "cpt_code": "47562",
                "scheduled_date": "2025-10-15T08:00:00Z",
                "surgeon": {
                    "id": "SURG-001",
                    "name": "Dr. Jane Smith",
                    "specialty": "General Surgery"
                },
                "patient_id": "PAT-789",
                "room": "OR-3",
                "estimated_duration_minutes": 90,
                "status": "scheduled",
                "notes": "Patient allergic to latex"
            }
        }


# ============================================================================
# Response Models
# ============================================================================

class ScheduledSurgery(BaseModel):
    """Scheduled surgery from EHR system for display in surgery schedule"""
    id: str = Field(..., description="Unique surgery ID")
    patientName: str = Field(..., description="Patient name (display-friendly, anonymized for POC)")
    surgeonName: str = Field(..., description="Surgeon full name")
    procedureName: str = Field(..., description="Surgical procedure name")
    orName: str = Field(..., description="Operating room identifier")
    startDateTime: str = Field(..., description="Scheduled start time (ISO 8601 format)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "SURG-001",
                "patientName": "John Smith",
                "surgeonName": "Dr. Sarah Johnson",
                "procedureName": "Total Knee Replacement",
                "orName": "OR-1",
                "startDateTime": "2025-11-12T07:30:00Z"
            }
        }


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")


class ServiceInfo(BaseModel):
    """Service information model"""
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    status: str = Field(..., description="Service status")
    docs: str = Field(..., description="API documentation URL")
