"""CDS Hooks — order-sign and order-sign/feedback endpoints."""

import logging

from fastapi import APIRouter

from .cds_hooks_models import CdsHookResponse, FeedbackRequest, log_feedback
from .contexts import OrderSignHookInput
from CDS.interop.bs.order_sign import get_bs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cds-services", tags=["CDS Hooks — order-sign"])


@router.post("/order-sign", response_model=CdsHookResponse)
async def order_sign(body: OrderSignHookInput) -> CdsHookResponse:
    """CDS Hooks — order-sign hook. Delegates to BS.OrderSign → BP.OrderSign."""
    logger.info("order-sign hook called: hookInstance=%s patientId=%s", body.hookInstance, body.context.patientId)
    rsp = get_bs().on_process_input(body)
    return rsp.response


@router.post("/order-sign/feedback", status_code=200)
async def order_sign_feedback(body: FeedbackRequest) -> None:
    """Receives clinician feedback on order-sign cards (accepted / overridden)."""
    log_feedback("order-sign", body.feedback)
