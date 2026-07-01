"""Business Process — patient-view CDS hook orchestrator.

Phase 1 (sequential, PoolSize=1):
  1. Extract patientId from hook context.
  2. Check prefetch for 'patientToGreet' (Patient resource).
     If absent, call BO.Fhir to retrieve the Patient.
  3. Extract age from Patient.birthDate (only required HAPI input in Phase 1;
     all other RiskAssessmentInput fields use their model defaults).
  4. Send RiskAssessmentInputRequest to BP.Hapi → RiskCalculationResult.
  5. Build CdsHookResponse cards from the risk result.
  6. Return PatientViewResponse.
"""

import logging
from datetime import date
from typing import Any, Optional

from iop import BusinessProcess, target

from DSE.models import RiskAssessmentInput
from DSE.interop.msg import RiskAssessmentInputRequest, RiskAssessmentResultResponse
from CDS.interop.msg.cds_hooks import (
    FhirReadRequest,
    PatientViewInputRequest,
    PatientViewResponse,
)
from CDS.routers.cds_hooks_models import (
    CdsAction,
    CdsCard,
    CdsHookResponse,
    CdsLink,
    CdsSource,
    CdsSuggestion,
    _MOLNLYCKE_SOURCE,
    build_smart_launch_url,
)

logger = logging.getLogger(__name__)


class PatientView(BusinessProcess):

    hapi_risk_target = target()
    fhir_target = target()

    def on_patient_view_request_message(
        self, request: PatientViewInputRequest
    ) -> PatientViewResponse:
        hook_request = request.input
        context = hook_request.context

        patient_id: str = context.patientId
        if not patient_id:
            raise ValueError("patientId missing from hook context")

        # --- Step 1: obtain the Patient FHIR resource ---
        patient = self._get_patient(hook_request, patient_id)

        # --- Step 2: extract HAPI inputs (Phase 1: age only, rest use model defaults) ---
        hapi_input = self._build_hapi_input(patient)

        # --- Step 3: calculate risk via BP.Hapi ---
        risk_request = RiskAssessmentInputRequest(input=hapi_input)
        risk_response: RiskAssessmentResultResponse = self.send_request_sync(self.hapi_risk_target, risk_request)
        risk = risk_response.result

        logger.info(
            "HAC PI risk for patient %s: %.1f%% (CI %.1f%%–%.1f%%, category=%s)",
            patient_id,
            risk.risk_percentage,
            risk.ci_lower,
            risk.ci_upper,
            risk.risk_category,
        )

        # --- Step 4: build cards ---
        smart_url = build_smart_launch_url(hook_request.fhirServer, patient_id)
        indicator = _risk_indicator(risk.risk_category)

        cards: list[CdsCard] = [
            # Card 1: information card (static, always "info")
            CdsCard(
                uuid="wound-care-info-001",
                summary="Pressure injury detected — Consider Mepilex Border",
                detail=(
                    "**Patient has a Stage 2-3 pressure injury documented on heel/sacrum.**\n\n"
                    "**Recommended product:** Mepilex Border — self-adherent soft silicone "
                    "multi-layer foam dressing with Safetac® technology.\n\n"
                    "Use as part of a comprehensive prevention protocol including support "
                    "surfaces, positioning, nutrition, and skin care."
                ),
                indicator="info",
                source=CdsSource(**_MOLNLYCKE_SOURCE),
                links=[
                    CdsLink(
                        label="Mepilex Border Product Family",
                        url="https://www.molnlycke.com/en-us/products/wound-care/bordered-foam-dressings/",
                        type="absolute",
                    )
                ],
            ),
            # Card 2: suggestion card — risk-adjusted indicator
            CdsCard(
                uuid="wound-care-suggestion-001",
                summary=f"HAC PI risk {risk.risk_percentage:.1f}% — Order Mepilex Border Heel",
                detail=(
                    f"**HAC PI Risk Score: {risk.risk_percentage:.1f}% "
                    f"(CI: {risk.ci_lower:.1f}%–{risk.ci_upper:.1f}%)**\n\n"
                    "Accepting this suggestion will create a SupplyRequest for "
                    "Mepilex Border Heel 22x23cm."
                ),
                indicator=indicator,
                source=CdsSource(**_MOLNLYCKE_SOURCE),
                suggestions=[
                    CdsSuggestion(
                        label="Order Mepilex Border Heel Dressing",
                        uuid="suggestion-mepilex-heel-001",
                        actions=[
                            CdsAction(
                                type="create",
                                description="Create supply request for Mepilex Border Heel 22x23cm",
                                resource={
                                    "resourceType": "SupplyRequest",
                                    "status": "active",
                                    "priority": "routine",
                                    "itemCodeableConcept": {
                                        "coding": [
                                            {
                                                "system": "http://www.molnlycke.com/products",
                                                "code": "282790",
                                                "display": "Mepilex Border Heel 22x23cm",
                                            }
                                        ],
                                        "text": "Mepilex Border Heel — foam dressing with Safetac",
                                    },
                                    "quantity": {"value": 5, "unit": "dressing"},
                                    "reasonReference": [
                                        {
                                            "reference": f"Patient/{patient_id}",
                                            "display": "HAC PI risk assessment",
                                        }
                                    ],
                                },
                            )
                        ],
                    )
                ],
                selectionBehavior="at-most-one",
            ),
            # Card 3: SMART app link — risk-adjusted indicator
            CdsCard(
                uuid="wound-care-smart-app-001",
                summary="Launch Mölnlycke Wound Care Decision Support App",
                detail=(
                    f"**HAC PI Risk Score: {risk.risk_percentage:.1f}% "
                    f"(CI: {risk.ci_lower:.1f}%–{risk.ci_upper:.1f}%)**\n\n"
                    "Launch the SMART app for the full risk calculator, product selection "
                    "wizard, and evidence-based prevention protocols."
                ),
                indicator=indicator,
                source=CdsSource(**_MOLNLYCKE_SOURCE),
                links=[
                    CdsLink(
                        label="Launch Wound Care Decision Support",
                        url=smart_url,
                        type="smart",
                        appContext=(
                            f'{{"patientId":"{patient_id}",'
                            f'"hacPiScore":{risk.risk_percentage:.1f},'
                            f'"hacPiCategory":"{risk.risk_category}",'
                            '"woundLocations":["heel","sacrum"],'
                            '"recommendedProducts":["282790"]}}'
                        ),
                    ),
                    CdsLink(
                        label="Mepilex Border Product Family",
                        url="https://www.molnlycke.com/en-us/products/wound-care/bordered-foam-dressings/",
                        type="absolute",
                    ),
                ],
            ),
        ]

        return PatientViewResponse(response=CdsHookResponse(cards=cards))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_patient(self, hook_request, patient_id: str) -> dict[str, Any]:
        """Return the Patient resource from prefetch, or fetch it from BO.Fhir."""
        if hook_request.prefetch is not None:
            patient = hook_request.prefetch.patient
            if patient:
                logger.debug("Patient %s resolved from prefetch", patient_id)
                return patient.model_dump(exclude_none=True)

        if not hook_request.fhirServer:
            raise ValueError(
                f"Patient {patient_id} not in prefetch and fhirServer not provided"
            )

        token: Optional[str] = (
            hook_request.fhirAuthorization.access_token
            if hook_request.fhirAuthorization
            else None
        )
        fhir_response = self.send_request_sync(
            self.fhir_target,
            FhirReadRequest(
                fhir_server=hook_request.fhirServer,
                resource_type="Patient",
                resource_id=patient_id,
                token=token,
            ),
        )
        logger.debug("Patient %s fetched from FHIR server", patient_id)
        return fhir_response.resource

    @staticmethod
    def _build_hapi_input(patient: dict[str, Any]) -> RiskAssessmentInput:
        """Extract HAPI model inputs from a FHIR Patient resource.

        Phase 1: only Patient.birthDate → age is used; all other inputs
        fall back to the model defaults defined in RiskAssessmentInput.
        """
        birth_date_str: Optional[str] = patient.get("birthDate")
        if not birth_date_str:
            raise ValueError("Patient resource missing required field: birthDate")
        birth_date = date.fromisoformat(birth_date_str)
        today = date.today()
        age = (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )
        return RiskAssessmentInput(age=age)


def _risk_indicator(risk_category: str) -> str:
    """Map HAC PI risk category to a CDS Hooks card indicator."""
    return {"low": "info", "moderate": "warning", "high": "critical"}.get(
        risk_category, "info"
    )
