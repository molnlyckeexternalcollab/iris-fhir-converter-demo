"""CDS Hooks — order-select and order-select/feedback endpoints."""

import logging

from fastapi import APIRouter

from .cds_hooks_models import (
    CdsCard,
    CdsHookRequest,
    CdsHookResponse,
    CdsSource,
    FeedbackRequest,
    _MOLNLYCKE_SOURCE,
    log_feedback,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cds-services", tags=["CDS Hooks — order-select"])


@router.post("/order-select", response_model=CdsHookResponse)
async def order_select(body: CdsHookRequest) -> CdsHookResponse:
    """CDS Hooks — order-select hook. Returns a simple informational card."""
    logger.info("order-select hook called: hookInstance=%s", body.hookInstance)

    return CdsHookResponse(cards=[
        CdsCard(
            uuid="order-select-info-001",
            summary="Order selection — Mölnlycke wound care products available",
            detail=(
                "Consider Mölnlycke wound care products for this patient. "
                "Launch the decision support app for personalised recommendations."
            ),
            indicator="info",
            source=CdsSource(**_MOLNLYCKE_SOURCE),
        )
    ])


@router.post("/order-select/feedback", status_code=200)
async def order_select_feedback(body: FeedbackRequest) -> None:
    """Receives clinician feedback on order-select cards (accepted / overridden)."""
    log_feedback("order-select", body.feedback)
