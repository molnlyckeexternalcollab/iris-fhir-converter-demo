"""Business Process — order-select CDS hook orchestrator.

Phase 1 (sequential, PoolSize=1):
  1. Extract the newly selected orders by matching context.selections against
     context.draftOrders (per CDS Hooks spec, decision support should focus
     on newly selected orders only, not the entire draft set).
  2. Build CDS cards:
     - Always: informational card listing relevant Mölnlycke wound care products.
     - When any newly selected order is a ServiceRequest or ProcedureRequest:
       also suggest a wound dressing change protocol (ServiceRequest).
"""

import logging
from typing import Any

from iop import BusinessProcess

from CDS.interop.msg.cds_hooks import OrderSelectRequest, OrderSelectResponse
from CDS.routers.cds_hooks_models import (
    CdsAction,
    CdsCard,
    CdsHookResponse,
    CdsLink,
    CdsSource,
    CdsSuggestion,
    _MOLNLYCKE_SOURCE,
)

logger = logging.getLogger(__name__)

# Resource types that indicate wound/procedure orders where dressing guidance is relevant
_WOUND_CARE_RESOURCE_TYPES = {"ServiceRequest", "ProcedureRequest"}


class OrderSelect(BusinessProcess):
    def on_order_select_request_message(
        self, request: OrderSelectRequest
    ) -> OrderSelectResponse:
        hook_input = request.input
        context = hook_input.context

        # Resolve the newly selected orders — the spec says to focus on these,
        # not on the full draftOrders bundle (which includes previously selected orders).
        selected_resources = _resolve_selections(
            context.selections,
            context.draftOrders,
        )

        logger.info(
            "order-select: patientId=%s newly selected=%s",
            context.patientId,
            context.selections,
        )

        cards = _build_cards(context.patientId, selected_resources)
        return OrderSelectResponse(response=CdsHookResponse(cards=cards))


def _resolve_selections(
    selections: list[str],
    draft_orders: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the Bundle entries whose id matches the selections array.

    selections contains relative references like "MedicationRequest/abc123".
    We strip the resource type prefix and match on the id field.
    """
    entries = draft_orders.get("entry", [])
    selected_ids = {ref.split("/")[-1] for ref in selections}
    return [
        entry["resource"]
        for entry in entries
        if entry.get("resource", {}).get("id") in selected_ids
    ]


def _build_cards(
    patient_id: str,
    selected_resources: list[dict[str, Any]],
) -> list[CdsCard]:
    cards: list[CdsCard] = [
        # Card 1 — always shown: product awareness
        CdsCard(
            uuid="wound-care-order-select-info-001",
            summary="Mölnlycke wound care products available for this patient",
            detail=(
                "When managing patients with wounds or at risk of pressure injury, "
                "consider Mölnlycke evidence-based dressings:\n\n"
                "- **Mepilex Border** — self-adherent soft silicone foam for pressure injuries "
                "(stages 2–3, heel/sacrum)\n"
                "- **Mepitel One** — single-layer wound contact layer for superficial or "
                "partial-thickness wounds\n"
                "- **Mepilex Transfer** — thin absorbent dressing for wounds with moderate exudate\n\n"
                "Use alongside a structured prevention protocol: repositioning schedule, "
                "nutritional support, and regular skin assessment."
            ),
            indicator="info",
            source=CdsSource(**_MOLNLYCKE_SOURCE),
            links=[
                CdsLink(
                    label="Mölnlycke Wound Care Product Selector",
                    url="https://www.molnlycke.com/en-us/products/wound-care/",
                    type="absolute",
                )
            ],
        )
    ]

    # Card 2 — only when the new selection includes a wound/procedure order:
    # suggest a dressing change protocol.
    has_procedure_order = any(
        r.get("resourceType") in _WOUND_CARE_RESOURCE_TYPES
        for r in selected_resources
    )

    if has_procedure_order:
        cards.append(
            CdsCard(
                uuid="wound-care-order-select-protocol-001",
                summary="Add Mepilex Border dressing change protocol",
                detail=(
                    "A structured dressing change protocol improves wound healing outcomes "
                    "and reduces the risk of infection.\n\n"
                    "**Suggested Mepilex Border protocol:**\n"
                    "- Change dressing every **3 days**, or sooner if saturated or dislodged\n"
                    "- Cleanse wound bed with **saline** before each change\n"
                    "- Document wound dimensions, exudate level, and periwound skin at each change\n"
                    "- Apply gentle pressure around edges after placement to activate Safetac® adhesion\n\n"
                    "Accepting this suggestion will add a wound dressing ServiceRequest to the order set."
                ),
                indicator="warning",
                source=CdsSource(**_MOLNLYCKE_SOURCE),
                suggestions=[
                    CdsSuggestion(
                        label="Add wound dressing change protocol — Mepilex Border every 3 days",
                        uuid="suggestion-wound-care-protocol-001",
                        isRecommended=True,
                        actions=[
                            CdsAction(
                                type="create",
                                description="Create wound care dressing change ServiceRequest",
                                resource={
                                    "resourceType": "ServiceRequest",
                                    "status": "draft",
                                    "intent": "order",
                                    "priority": "routine",
                                    "code": {
                                        "coding": [
                                            {
                                                "system": "http://snomed.info/sct",
                                                "code": "182531007",
                                                "display": "Dressing of wound",
                                            }
                                        ],
                                        "text": "Wound dressing change — Mepilex Border, every 3 days",
                                    },
                                    "subject": {"reference": f"Patient/{patient_id}"},
                                    "occurrenceTiming": {
                                        "repeat": {
                                            "frequency": 1,
                                            "period": 3,
                                            "periodUnit": "d",
                                        }
                                    },
                                    "patientInstruction": (
                                        "Apply Mepilex Border dressing to the wound. "
                                        "Cleanse with saline before each change. "
                                        "Replace every 3 days or sooner if saturated."
                                    ),
                                },
                            )
                        ],
                    )
                ],
                selectionBehavior="at-most-one",
            )
        )

    return cards

