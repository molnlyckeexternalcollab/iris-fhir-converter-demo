"""
Pydantic models for DSE (Decision Support Engine) service.

FastAPI will auto-generate OpenAPI schemas from these models.
"""

from typing import Literal
from pydantic import BaseModel, Field, computed_field

from CDS.models import BradenActivityScore, BradenFrictionScore, BradenMobilityScore, BradenMoistureScore, BradenSensoryScore, GaitTransferScore


# ============================================================================
# HAC PI Risk Calculator Models
# ============================================================================

class RiskAssessmentInput(BaseModel):
    """
    Complete patient data for HAC PI risk calculation.
    Follows Reese et al. (2024) model specification.
    """
    
    # Patient Demographics
    age: int = Field(
        ..., 
        ge=0, 
        le=150, 
        description="Patient age in years (required, 0-150)"
    )
    
    # Clinical Measurements (lab values with defaults per model)
    albumin: float = Field(
        default=3.6, 
        ge=0.0, 
        description="Albumin level (default: 3.6 if missing)"
    )
    bun: float = Field(
        default=16.0, 
        ge=0.0, 
        description="Blood Urea Nitrogen (default: 16 if missing)"
    )
    chloride: float = Field(
        default=105.0, 
        ge=0.0, 
        description="Chloride level (default: 105 if missing)"
    )
    rdw_cv: float = Field(
        default=13.9, 
        ge=0.0, 
        description="Red Cell Distribution Width CV (default: 13.9 if missing)"
    )
    
    # Braden Scale Assessment (5 components)
    braden_mobility: BradenMobilityScore = Field(
        default=BradenMobilityScore.MISSING,
        description="Braden Mobility score"
    )
    braden_moisture: BradenMoistureScore = Field(
        default=BradenMoistureScore.MISSING,
        description="Braden Moisture score"
    )
    braden_activity: BradenActivityScore = Field(
        default=BradenActivityScore.MISSING,
        description="Braden Activity score"
    )
    braden_friction: BradenFrictionScore = Field(
        default=BradenFrictionScore.MISSING,
        description="Braden Friction and Shear score"
    )
    braden_sensory: BradenSensoryScore = Field(
        default=BradenSensoryScore.MISSING,
        description="Braden Sensory Perception score"
    )
    
    # Gait and Transfer Assessment
    gait_transfer: GaitTransferScore = Field(
        default=GaitTransferScore.MISSING,
        description="Gait impairment score"
    )
    
    # Medical Devices (binary indicators)
    has_tracheostomy: bool = Field(
        default=False, 
        description="Patient has had a tracheostomy"
    )
    has_central_line: bool = Field(
        default=False, 
        description="Patient has a central line in place"
    )
    has_chest_tube: bool = Field(
        default=False, 
        description="Patient has a chest tube in place"
    )
    has_ostomy: bool = Field(
        default=False, 
        description="Patient has an ostomy in place"
    )
    is_on_ecmo: bool = Field(
        default=False, 
        description="Patient is on ECMO device"
    )
    
    # Clinical Conditions (binary indicators)
    has_edema: bool = Field(
        default=False, 
        description="Patient has edema present"
    )
    has_spinal_cord_injury: bool = Field(
        default=False, 
        description="Patient has a spinal cord injury"
    )
    is_icu_admitted: bool = Field(
        default=False, 
        description="Patient is admitted to an ICU"
    )
    is_on_gim_service: bool = Field(
        default=False, 
        description="Patient is on General Internal Medicine service"
    )
    is_on_vasopressin: bool = Field(
        default=False, 
        description="Patient is on vasopressin medication"
    )
    is_on_cardio_sympathomimetic: bool = Field(
        default=False, 
        description="Patient is on cardiovascular sympathomimetic medication"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "age": 65,
                "albumin": 3.2,
                "bun": 18,
                "chloride": 102,
                "rdw_cv": 14.5,
                "braden_mobility": "2",
                "braden_moisture": "3",
                "braden_activity": "2",
                "braden_friction": "2",
                "braden_sensory": "3",
                "gait_transfer": "10",
                "has_tracheostomy": False,
                "has_central_line": True,
                "has_chest_tube": False,
                "has_ostomy": False,
                "is_on_ecmo": False,
                "has_edema": True,
                "has_spinal_cord_injury": False,
                "is_icu_admitted": True,
                "is_on_gim_service": False,
                "is_on_vasopressin": False,
                "is_on_cardio_sympathomimetic": False
            }
        }


RiskCategory = Literal["low", "moderate", "high"]


class RiskCalculationResult(BaseModel):
    """
    Result of HAC PI risk calculation with confidence interval.
    """
    
    risk_percentage: float = Field(
        ..., 
        ge=0.0, 
        le=100.0,
        description="Point estimate of risk as percentage (0-100)"
    )
    
    ci_lower: float = Field(
        ..., 
        ge=0.0, 
        le=100.0,
        description="Lower bound of 95% confidence interval (percentage)"
    )
    
    ci_upper: float = Field(
        ..., 
        ge=0.0, 
        le=100.0,
        description="Upper bound of 95% confidence interval (percentage)"
    )
    
    z_score: float = Field(
        ...,
        description="Linear predictor Z from logistic regression equation"
    )
    
    @computed_field
    @property
    def risk_category(self) -> RiskCategory:
        """
        Categorical risk level based on thresholds:
        - low: <1%
        - moderate: 1-5%
        - high: >5%
        """
        if self.risk_percentage < 1.0:
            return "low"
        elif self.risk_percentage < 5.0:
            return "moderate"
        else:
            return "high"
    
    @computed_field
    @property
    def risk_color(self) -> str:
        """
        Color code for UI display:
        - green (#4caf50): low risk
        - yellow/orange (#ff9800): moderate risk
        - red (#f44336): high risk
        """
        if self.risk_category == "low":
            return "#4caf50"
        elif self.risk_category == "moderate":
            return "#ff9800"
        else:
            return "#f44336"
    
    class Config:
        json_schema_extra = {
            "example": {
                "risk_percentage": 2.3,
                "ci_lower": 1.8,
                "ci_upper": 2.9,
                "z_score": -3.76,
                "risk_category": "moderate",
                "risk_color": "#ff9800"
            }
        }

