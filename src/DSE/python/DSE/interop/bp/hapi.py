"""Business Process — HAPI risk calculator."""

from fastapi import HTTPException
from iop import BusinessProcess
from pydantic import ValidationError

from DSE.fhir_extraction import extract_risk_input_from_bundle
from DSE.hapi_calculator import calculate_risk
from DSE.models import RiskAssessmentInput, RiskCalculationResult
from DSE.interop.msg import RiskAssessmentBundleRequest, RiskAssessmentInputRequest, RiskAssessmentResultResponse


class Hapi(BusinessProcess):
    def on_risk_assessment_input_request_message(
        self, request: RiskAssessmentInputRequest
    ) -> RiskAssessmentResultResponse:
        result: RiskCalculationResult = self._calculate_hapi_risk(request.input)
        return RiskAssessmentResultResponse(result=result)

    def on_risk_assessment_bundle_request_message(
        self, request: RiskAssessmentBundleRequest
    ) -> RiskAssessmentResultResponse:
        """Extract inputs from the bundle, then run the same calculation path."""
        try:
            input_data = extract_risk_input_from_bundle(request.bundle)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        result: RiskCalculationResult = self._calculate_hapi_risk(input_data)
        return RiskAssessmentResultResponse(result=result)

    def _calculate_hapi_risk(self, input_data: RiskAssessmentInput) -> RiskCalculationResult:
        """
        Calculate Hospital Acquired Pressure Injury (HAC PI) risk.

        Uses the Reese et al. (2024) validated logistic regression model to compute
        pressure injury risk from patient demographics, clinical measurements, Braden
        Scale assessments, medical devices, and clinical conditions.

        **Algorithm**: Logistic regression with 35+ coefficients
        - Z = intercept + Σ(coefficient_i * variable_i)
        - P = 1 / (1 + exp(-Z))
        - 95% CI computed via Delta method

        **Performance**: <100ms calculation time

        **Stateless**: No data persistence, suitable for real-time clinical use

        Args:
            input_data: Patient assessment data (age required, other fields optional with defaults)

        Returns:
            RiskCalculationResult with risk percentage, 95% CI, Z-score, category, and color

        Raises:
            HTTPException 422: Validation error (invalid input data)
            HTTPException 500: Internal calculation error
        """
        try:
            return calculate_risk(input_data)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
