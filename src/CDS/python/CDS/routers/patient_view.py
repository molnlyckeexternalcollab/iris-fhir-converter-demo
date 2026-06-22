"""CDS Hooks — patient-view and patient-view/feedback endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import Field

from .cds_hooks_models import (
    CdsCard,
    CdsHookRequest,
    CdsHookResponse,
    CdsLink,
    CdsSuggestion,
    CdsSource,
    FeedbackRequest,
    CdsAction,
    HookContext,
    _MOLNLYCKE_SOURCE,
    build_smart_launch_url,
    log_feedback,
)
from .epic_extensions import get_epic_extensions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cds-services", tags=["CDS Hooks — patient-view"])


class PatientViewContext(HookContext):
    """Context for the ``patient-view`` hook.

    See: <a href="https://build.fhir.org/ig/HL7/cds-hooks-library/en/patient-view.html">patient-view hook spec</a>
    """
    userId: str = Field(
        description="The id of the current user in [ResourceType]/[id] format. "
                    "For this hook, expected to be Practitioner, PractitionerRole, Patient, or RelatedPerson. "
                    "For example: Practitioner/abc or Patient/123.",
    )
    patientId: str = Field(
        description="The FHIR Patient.id of the current patient in context.",
    )
    encounterId: Optional[str] = Field(
        default=None,
        description="The FHIR Encounter.id of the current encounter in context. OPTIONAL.",
    )


class PatientViewRequest(CdsHookRequest):
    """CDS Hooks request body for the ``patient-view`` hook.

    Vendor-neutral: accepts requests from any CDS client (Epic, Cerner, etc.).
    Epic vendor extensions, if present, can be accessed via
    ``get_epic_extensions(body)`` inside the handler.
    """
    context: PatientViewContext  # type: ignore[assignment]


@router.post("/patient-view", response_model=CdsHookResponse)
async def patient_view(body: PatientViewRequest) -> CdsHookResponse:
    """CDS Hooks — patient-view hook.

    Returns a set of dummy cards demonstrating the three main card types:
    information, suggestion (with FHIR action), and SMART app link.
    """
    logger.info(
        "patient-view hook called: hookInstance=%s patientId=%s",
        body.hookInstance,
        body.context.patientId,
    )

    # Opportunistically parse Epic extensions — None for non-Epic callers.
    epic_ext = get_epic_extensions(body)
    if epic_ext is not None:
        logger.debug("Epic caller detected — trigger=%s epic_version=%s",
                     epic_ext.bpa_trigger_action, epic_ext.epic_version)

    patient_id = body.context.patientId
    smart_url = build_smart_launch_url(body.fhirServer, patient_id)

    cards: list[CdsCard] = [
        # --- Card 1: information card ---
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
        # --- Card 2: suggestion card with FHIR action ---
        CdsCard(
            uuid="wound-care-suggestion-001",
            summary="High risk for pressure injury — Order Mepilex Border Heel",
            detail=(
                "**HAC PI Risk Score: 24.3% (CI: 18.1%–31.8%)**\n\n"
                "Elevated risk factors: Stage 2-3 pressure injury, Braden score 14, "
                "limited mobility, ICU admission, multiple medical devices.\n\n"
                "Accepting this suggestion will create a SupplyRequest for "
                "Mepilex Border Heel 22x23cm."
            ),
            indicator="warning",
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
                                        "reference": "Condition/pressure-injury-heel",
                                        "display": "Stage 2-3 Pressure Injury — Heel",
                                    }
                                ],
                            },
                        )
                    ],
                )
            ],
            selectionBehavior="at-most-one",
        ),
        # --- Card 3: SMART app link card ---
        CdsCard(
            uuid="wound-care-smart-app-001",
            summary="Launch Mölnlycke Wound Care Decision Support App",
            detail=(
                "**HAC PI Risk Score: 24.3% (CI: 18.1%–31.8%)**\n\n"
                "Launch the SMART app for the full risk calculator, product selection "
                "wizard, and evidence-based prevention protocols."
            ),
            indicator="critical",
            source=CdsSource(**_MOLNLYCKE_SOURCE),
            links=[
                CdsLink(
                    label="Launch Wound Care Decision Support",
                    url=smart_url,
                    type="smart",
                    appContext=(
                        f'{{"patientId":"{patient_id}",'
                        '"hacPiScore":24.3,"bradenScore":14,'
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

    return CdsHookResponse(cards=cards)


@router.post("/patient-view/feedback", status_code=200)
async def patient_view_feedback(body: FeedbackRequest) -> None:
    """Receives clinician feedback on patient-view cards (accepted / overridden)."""
    log_feedback("patient-view", body.feedback)
