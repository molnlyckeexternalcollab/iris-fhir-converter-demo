"""CDS Hooks — patient-view and patient-view/feedback endpoints."""

import logging

from fastapi import APIRouter

from .cds_hooks_models import (
    CdsHookResponse,
    FeedbackRequest,
    log_feedback,
)
from .contexts import PatientViewHookInput
from .epic_extensions import get_epic_extensions
from CDS.interop.bs.patient_view import get_bs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cds-services", tags=["CDS Hooks — patient-view"])


@router.post("/patient-view", response_model=CdsHookResponse)
async def patient_view(body: PatientViewHookInput) -> CdsHookResponse:
    """CDS Hooks — patient-view hook.

    Delegates to BS.PatientView → BP.PatientView (IRIS production) which
    performs prefetch resolution, HAC PI risk calculation via BP.Hapi, and
    card building before returning the CdsHookResponse.
    """
    logger.info(
        "patient-view hook called: hookInstance=%s patientId=%s",
        body.hookInstance,
        body.context.patientId,
    )

    # Opportunistically parse Epic extensions — None for non-Epic callers.
    epic_ext = get_epic_extensions(body)
    if epic_ext is not None:
        logger.info(
            "Epic caller detected — "
            "trigger=%s | cds_hooks_spec=%s | fhir_version=%s | "
            "criteria_id=%s | epic_version=%s | impl_version=%s",
            epic_ext.bpa_trigger_action,
            epic_ext.cds_hooks_specification_version,
            epic_ext.fhir_version,
            epic_ext.criteria_id,
            epic_ext.epic_version,
            epic_ext.cds_hooks_implementation_version,
        )

    rsp = get_bs().on_process_input(body)
    return rsp.response


@router.post("/patient-view/feedback", status_code=200)
async def patient_view_feedback(body: FeedbackRequest) -> None:
    """Receives clinician feedback on patient-view cards (accepted / overridden)."""
    log_feedback("patient-view", body.feedback)
