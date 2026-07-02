"""CDS Hooks — order-select and order-select/feedback endpoints."""

import logging

from fastapi import APIRouter

from .cds_hooks_models import CdsHookResponse, FeedbackRequest, log_feedback
from .contexts import OrderSelectHookInput
from CDS.interop.bs.order_select import get_bs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cds-services", tags=["CDS Hooks — order-select"])


@router.post("/order-select", response_model=CdsHookResponse)
async def order_select(body: OrderSelectHookInput) -> CdsHookResponse:
    """CDS Hooks — order-select hook. Delegates to BS.OrderSelect → BP.OrderSelect."""
    logger.info("order-select hook called: hookInstance=%s patientId=%s", body.hookInstance, body.context.patientId)
    rsp = get_bs().on_process_input(body)
    return rsp.response


@router.post("/order-select/feedback", status_code=200)
async def order_select_feedback(body: FeedbackRequest) -> None:
    """Receives clinician feedback on order-select cards (accepted / overridden)."""
    log_feedback("order-select", body.feedback)
