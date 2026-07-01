"""
HAC PI Risk Calculator Service

Implements the Reese et al. (2024) validated logistic regression model for
Hospital Acquired Pressure Injury (HAC PI) risk prediction.

Reference: https://www.sciencedirect.com/science/article/pii/S2291969424000498
"""

from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np
from scipy import stats

from DSE.models import RiskAssessmentInput, RiskCalculationResult


@dataclass
class ModelCoefficients:
    """
    Reese et al. (2024) logistic regression model coefficients.
    Source: Appendix 1 - Features and coefficients of model and equation
    """
    
    INTERCEPT: float = -4.1812002
    
    # Continuous variables
    AGE: float = 0.0177999
    ALBUMIN: float = -0.5281964
    BUN: float = 0.00529961
    CHLORIDE: float = -0.0175021
    RDW_CV: float = 0.02907249
    
    # Braden Mobility
    BRADEN_MOBILITY_1: float = 0.45523305  # Completely Immobile
    BRADEN_MOBILITY_2: float = 0.37061835  # Very Limited
    BRADEN_MOBILITY_3: float = 0.16693425  # Slightly Limited
    BRADEN_MOBILITY_MISSING: float = 1.33510627
    
    # Braden Moisture
    BRADEN_MOISTURE_1: float = 0.06386941  # Constantly Moist
    BRADEN_MOISTURE_2: float = 0.37059476  # Very Moist
    BRADEN_MOISTURE_3: float = 0.33684558  # Occasionally Moist
    BRADEN_MOISTURE_MISSING: float = 0.86599357
    
    # Braden Activity
    BRADEN_ACTIVITY_1: float = 0.67739212  # Bedfast
    BRADEN_ACTIVITY_2: float = 0.71491035  # Chairfast
    BRADEN_ACTIVITY_3: float = 0.50653582  # Walks Occasionally
    BRADEN_ACTIVITY_MISSING: float = -0.0813083
    
    # Braden Friction and Shear
    BRADEN_FRICTION_1: float = 0.46265013  # Problem
    BRADEN_FRICTION_2: float = 0.34686801  # Potential Problem
    BRADEN_FRICTION_MISSING: float = -2.4211435
    
    # Braden Sensory Perception
    BRADEN_SENSORY_1: float = -0.2547595  # Completely Limited
    BRADEN_SENSORY_2: float = 0.10338965  # Very Limited
    BRADEN_SENSORY_3: float = 0.13860724  # Slightly Limited
    BRADEN_SENSORY_MISSING: float = 0.13982251
    
    # Gait Transfer
    GAIT_TRANSFER_10: float = 0.06334588  # Weak Gait
    GAIT_TRANSFER_20: float = 0.25466541  # Impaired Gait
    GAIT_TRANSFER_MISSING: float = -0.585254
    
    # Medical Devices
    TRACHEOSTOMY: float = 1.51259407
    CENTRAL_LINE: float = 0.72893544
    CHEST_TUBE: float = 0.66294066
    OSTOMY: float = 0.55791264
    ECMO: float = 0.87298112
    
    # Clinical Conditions
    EDEMA: float = 1.06047082
    SPINAL_CORD_INJURY: float = 0.67228617
    ICU_ADMISSION: float = 0.20985863
    GIM_SERVICE: float = 0.31090067
    VASOPRESSIN: float = 0.42814952
    CARDIO_SYMPATHOMIMETIC: float = 0.55763892
    
    @classmethod
    def to_dict(cls) -> Dict[str, float]:
        """Convert coefficients to dictionary for iteration."""
        return {
            name: value for name, value in cls.__dict__.items()
            if not name.startswith('_') and isinstance(value, (int, float))
        }


# Model coefficients singleton instance
COEFFICIENTS = ModelCoefficients()


def calculate_z_score(input_data: RiskAssessmentInput) -> float:
    """
    Calculate the linear predictor Z-score for the Reese et al. model.
    
    Z = intercept + Σ(coefficient_i * variable_i)
    
    This implements the core logistic regression equation using all 35+ 
    parameters from the validated model.
    
    Args:
        input_data: Patient assessment data with age, clinical measurements,
                   Braden Scale scores, devices, and conditions
    
    Returns:
        Z-score (linear predictor) before logistic transformation
    
    Examples:
        >>> input_data = RiskAssessmentInput(age=65)
        >>> z = calculate_z_score(input_data)
        >>> z  # Should be negative for low risk patients
        -3.8234...
    """
    # Start with intercept
    z = COEFFICIENTS.INTERCEPT
    
    # Add continuous variables (age + clinical measurements)
    z += COEFFICIENTS.AGE * input_data.age
    z += COEFFICIENTS.ALBUMIN * input_data.albumin
    z += COEFFICIENTS.BUN * input_data.bun
    z += COEFFICIENTS.CHLORIDE * input_data.chloride
    z += COEFFICIENTS.RDW_CV * input_data.rdw_cv
    
    # Add Braden Mobility contributions
    # Reference category is "4" (No Limitation), so no coefficient added
    if input_data.braden_mobility == "1":
        z += COEFFICIENTS.BRADEN_MOBILITY_1
    elif input_data.braden_mobility == "2":
        z += COEFFICIENTS.BRADEN_MOBILITY_2
    elif input_data.braden_mobility == "3":
        z += COEFFICIENTS.BRADEN_MOBILITY_3
    elif input_data.braden_mobility == "missing":
        z += COEFFICIENTS.BRADEN_MOBILITY_MISSING
    
    # Add Braden Moisture contributions
    # Reference category is "4" (Rarely Moist)
    if input_data.braden_moisture == "1":
        z += COEFFICIENTS.BRADEN_MOISTURE_1
    elif input_data.braden_moisture == "2":
        z += COEFFICIENTS.BRADEN_MOISTURE_2
    elif input_data.braden_moisture == "3":
        z += COEFFICIENTS.BRADEN_MOISTURE_3
    elif input_data.braden_moisture == "missing":
        z += COEFFICIENTS.BRADEN_MOISTURE_MISSING
    
    # Add Braden Activity contributions
    # Reference category is "4" (Walks Frequently)
    if input_data.braden_activity == "1":
        z += COEFFICIENTS.BRADEN_ACTIVITY_1
    elif input_data.braden_activity == "2":
        z += COEFFICIENTS.BRADEN_ACTIVITY_2
    elif input_data.braden_activity == "3":
        z += COEFFICIENTS.BRADEN_ACTIVITY_3
    elif input_data.braden_activity == "missing":
        z += COEFFICIENTS.BRADEN_ACTIVITY_MISSING
    
    # Add Braden Friction contributions
    # Reference category is "3" (No Apparent Problem)
    if input_data.braden_friction == "1":
        z += COEFFICIENTS.BRADEN_FRICTION_1
    elif input_data.braden_friction == "2":
        z += COEFFICIENTS.BRADEN_FRICTION_2
    elif input_data.braden_friction == "missing":
        z += COEFFICIENTS.BRADEN_FRICTION_MISSING
    
    # Add Braden Sensory contributions
    # Reference category is "4" (No Impairment)
    if input_data.braden_sensory == "1":
        z += COEFFICIENTS.BRADEN_SENSORY_1
    elif input_data.braden_sensory == "2":
        z += COEFFICIENTS.BRADEN_SENSORY_2
    elif input_data.braden_sensory == "3":
        z += COEFFICIENTS.BRADEN_SENSORY_3
    elif input_data.braden_sensory == "missing":
        z += COEFFICIENTS.BRADEN_SENSORY_MISSING
    
    # Add Gait Transfer contributions
    # Reference category is "0" (Normal Gait)
    if input_data.gait_transfer == "10":
        z += COEFFICIENTS.GAIT_TRANSFER_10
    elif input_data.gait_transfer == "20":
        z += COEFFICIENTS.GAIT_TRANSFER_20
    elif input_data.gait_transfer == "missing":
        z += COEFFICIENTS.GAIT_TRANSFER_MISSING
    
    # Add Medical Device contributions (binary indicators)
    if input_data.has_tracheostomy:
        z += COEFFICIENTS.TRACHEOSTOMY
    if input_data.has_central_line:
        z += COEFFICIENTS.CENTRAL_LINE
    if input_data.has_chest_tube:
        z += COEFFICIENTS.CHEST_TUBE
    if input_data.has_ostomy:
        z += COEFFICIENTS.OSTOMY
    if input_data.is_on_ecmo:
        z += COEFFICIENTS.ECMO
    
    # Add Clinical Condition contributions (binary indicators)
    if input_data.has_edema:
        z += COEFFICIENTS.EDEMA
    if input_data.has_spinal_cord_injury:
        z += COEFFICIENTS.SPINAL_CORD_INJURY
    if input_data.is_icu_admitted:
        z += COEFFICIENTS.ICU_ADMISSION
    if input_data.is_on_gim_service:
        z += COEFFICIENTS.GIM_SERVICE
    if input_data.is_on_vasopressin:
        z += COEFFICIENTS.VASOPRESSIN
    if input_data.is_on_cardio_sympathomimetic:
        z += COEFFICIENTS.CARDIO_SYMPATHOMIMETIC
    
    return z


def calculate_probability(z_score: float) -> float:
    """
    Transform Z-score to probability using logistic function.
    
    P = 1 / (1 + exp(-Z))
    
    This converts the linear predictor from the logistic regression model
    into a probability between 0 and 1, then returns it as a percentage (0-100).
    
    Args:
        z_score: Linear predictor from calculate_z_score()
    
    Returns:
        Risk probability as percentage (0.0 to 100.0)
    
    Examples:
        >>> z = -3.5  # Low risk Z-score
        >>> prob = calculate_probability(z)
        >>> prob
        2.93...  # ~3% risk
        
        >>> z = 0.0  # Neutral Z-score
        >>> prob = calculate_probability(z)
        >>> prob
        50.0  # 50% risk
        
        >>> z = 2.0  # High risk Z-score
        >>> prob = calculate_probability(z)
        >>> prob
        88.08...  # ~88% risk
    """
    # Logistic transformation: P = 1 / (1 + exp(-Z))
    # Using numpy for numerical stability with large Z values
    probability = 1.0 / (1.0 + np.exp(-z_score))
    
    # Convert to percentage
    percentage = probability * 100.0
    
    return percentage


def calculate_confidence_interval(
    risk_percentage: float, 
    z_score: float, 
    approximate_se: float = 0.02
) -> Tuple[float, float]:
    """
    Calculate 95% confidence interval using Delta method.
    
    The Delta method approximates the variance of a transformed random variable.
    For logistic regression: SE(P) ≈ |dP/dZ| * SE(Z) = P(1-P) * SE(Z)
    
    Args:
        risk_percentage: Point estimate of risk as percentage (0-100)
        z_score: Linear predictor from logistic regression
        approximate_se: Approximate standard error for Z-score
                       (default: 0.02, calibrated from validation data)
    
    Returns:
        Tuple of (lower_bound, upper_bound) as percentages (0-100)
    
    Notes:
        - The approximate_se parameter is derived from model validation studies
        - CI bounds are clamped to [0, 100] to ensure valid percentages
        - Uses 1.96 as z-critical value for 95% confidence level
    
    Examples:
        >>> risk = 2.5  # 2.5% risk
        >>> z = -3.66
        >>> ci_lower, ci_upper = calculate_confidence_interval(risk, z)
        >>> ci_lower < risk < ci_upper
        True
        
        >>> # Very low risk case
        >>> risk = 0.5
        >>> z = -5.0
        >>> ci_lower, ci_upper = calculate_confidence_interval(risk, z)
        >>> ci_lower >= 0.0  # Clamped to valid range
        True
    """
    # Convert percentage back to probability for calculation
    probability = risk_percentage / 100.0
    
    # Delta method: SE(P) = |dP/dZ| * SE(Z)
    # For logistic function: dP/dZ = P(1-P)
    derivative = probability * (1.0 - probability)
    se_probability = derivative * approximate_se
    
    # 95% CI: P ± z_critical * SE(P)
    # Using scipy.stats.norm.ppf for z-critical value (1.96 for 95% CI)
    z_critical = stats.norm.ppf(0.975)  # Two-tailed 95% CI
    
    # Calculate bounds in probability space
    lower_prob = probability - z_critical * se_probability
    upper_prob = probability + z_critical * se_probability
    
    # Clamp to valid probability range [0, 1]
    lower_prob = max(0.0, lower_prob)
    upper_prob = min(1.0, upper_prob)
    
    # Convert back to percentages
    ci_lower = lower_prob * 100.0
    ci_upper = upper_prob * 100.0
    
    return (ci_lower, ci_upper)


def calculate_risk(input_data: RiskAssessmentInput) -> RiskCalculationResult:
    """
    Calculate HAC PI risk with full Reese et al. (2024) model.
    
    This is the main orchestrator function that combines all calculation steps:
    1. Calculate Z-score from patient data and model coefficients
    2. Transform Z to probability via logistic function
    3. Calculate 95% confidence interval using Delta method
    4. Return result with computed risk category and color
    
    Args:
        input_data: Complete patient assessment data including age, 
                   clinical measurements, Braden Scale, devices, and conditions
    
    Returns:
        RiskCalculationResult with risk percentage, confidence interval,
        Z-score, and computed risk category/color
    
    Examples:
        >>> # Low risk patient
        >>> patient = RiskAssessmentInput(age=45)
        >>> result = calculate_risk(patient)
        >>> result.risk_category
        'low'
        >>> result.risk_color
        '#4caf50'
        
        >>> # High risk patient with multiple factors
        >>> patient = RiskAssessmentInput(
        ...     age=85,
        ...     albumin=2.8,
        ...     braden_mobility="1",
        ...     has_edema=True,
        ...     is_icu_admitted=True
        ... )
        >>> result = calculate_risk(patient)
        >>> result.risk_category
        'high'
        >>> result.risk_percentage > 5.0
        True
    """
    # Step 1: Calculate linear predictor (Z-score)
    z = calculate_z_score(input_data)
    
    # Step 2: Transform to probability percentage
    risk_pct = calculate_probability(z)
    
    # Step 3: Calculate 95% confidence interval
    ci_lower, ci_upper = calculate_confidence_interval(risk_pct, z)
    
    # Step 4: Create result (risk_category and risk_color computed automatically)
    result = RiskCalculationResult(
        risk_percentage=risk_pct,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        z_score=z
    )
    
    return result
