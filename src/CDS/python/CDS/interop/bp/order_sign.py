"""Business Process — order-sign CDS hook orchestrator.

order-sign is the final step before orders are committed. Unlike order-select,
there is no 'selections' array — the entire draftOrders bundle is being signed.
This is the last chance for the clinician to revise.

Phase 1 logic (sequential, PoolSize=1):
  1. Scan all orders in draftOrders for two signals:
     a. NSAID medications — NSAIDs are known to impair wound healing by inhibiting
        prostaglandin synthesis. At signing time, flag this and suggest adding a
        protective wound dressing if the patient has or is at risk of skin breakdown.
     b. Wound care orders (ServiceRequest/ProcedureRequest) — confirm the dressing
        selection is appropriate and the protocol is complete before committing.
  2. Return the relevant cards. An empty cards list is a valid response (no signal found).
"""

import logging
from typing import Any

from iop import BusinessProcess

from CDS.interop.msg.cds_hooks import OrderSignRequest, OrderSignResponse
from CDS.routers.cds_hooks_models import (
    CdsAction,
    CdsCard,
    CdsHookResponse,
    CdsLink,
    CdsSource,
    CdsSuggestion,
    _COMPANY_SOURCE,
)

logger = logging.getLogger(__name__)

# RxNorm codes for common NSAIDs (non-exhaustive — real implementation would
# query a terminology service or use a curated ValueSet)
_NSAID_RXNORM_CODES = {
    "5640",    # ibuprofen
    "41493",   # naproxen
    "7258",    # piroxicam
    "3355",    # diclofenac
    "35827",   # celecoxib
    "41267",   # meloxicam
    "1223",    # aspirin (high-dose analgesic use)
    "36567",   # indomethacin
}

_WOUND_CARE_RESOURCE_TYPES = {"ServiceRequest", "ProcedureRequest"}


class OrderSign(BusinessProcess):
    def on_order_sign_request_message(
        self, request: OrderSignRequest
    ) -> OrderSignResponse:
        hook_input = request.input
        context = hook_input.context
        entries = context.draftOrders.get("entry", [])
        resources = [e["resource"] for e in entries if "resource" in e]

        logger.info(
            "order-sign: patientId=%s total orders being signed=%d",
            context.patientId,
            len(resources),
        )

        cards: list[CdsCard] = []

        nsaid_orders = _find_nsaid_orders(resources)
        if nsaid_orders:
            cards.append(_nsaid_warning_card(context.patientId, nsaid_orders))

        wound_care_orders = [
            r for r in resources
            if r.get("resourceType") in _WOUND_CARE_RESOURCE_TYPES
        ]
        if wound_care_orders:
            cards.append(_wound_care_confirmation_card(context.patientId))

        return OrderSignResponse(response=CdsHookResponse(cards=cards))


# ---------------------------------------------------------------------------
# Signal detection helpers
# ---------------------------------------------------------------------------

def _find_nsaid_orders(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return MedicationRequest resources that reference a known NSAID."""
    nsaids = []
    for r in resources:
        if r.get("resourceType") != "MedicationRequest":
            continue
        if _is_nsaid(r):
            nsaids.append(r)
    return nsaids


def _is_nsaid(medication_request: dict[str, Any]) -> bool:
    """Check medicationCodeableConcept or contained Medication resource for NSAID RxNorm codes."""
    # Direct codeable concept on the request
    concept = medication_request.get("medicationCodeableConcept", {})
    if _codings_contain_nsaid(concept.get("coding", [])):
        return True

    # medicationReference — the Medication resource may be in the same bundle
    # (Epic Feb 2024+ includes it as a contained resource). We check display as
    # a fallback since we don't resolve the reference here.
    ref = medication_request.get("medicationReference", {})
    display = ref.get("display", "").lower()
    return any(name in display for name in ("ibuprofen", "naproxen", "diclofenac",
                                             "celecoxib", "meloxicam", "piroxicam",
                                             "indomethacin"))


def _codings_contain_nsaid(codings: list[dict[str, Any]]) -> bool:
    for coding in codings:
        if (coding.get("system") == "http://www.nlm.nih.gov/research/umls/rxnorm"
                and coding.get("code") in _NSAID_RXNORM_CODES):
            return True
    return False


# ---------------------------------------------------------------------------
# Card builders
# ---------------------------------------------------------------------------

def _nsaid_warning_card(patient_id: str, nsaid_orders: list[dict[str, Any]]) -> CdsCard:
    med_names = ", ".join(
        o.get("medicationReference", {}).get("display")
        or o.get("medicationCodeableConcept", {}).get("text", "unknown")
        for o in nsaid_orders
    )
    return CdsCard(
        uuid="wound-care-nsaid-warning-001",
        summary="NSAIDs being signed — consider wound healing impact",
        detail=(
            f"**{med_names}** is an NSAID. NSAIDs inhibit prostaglandin synthesis, "
            "which plays a role in the inflammatory phase of wound healing. "
            "Prolonged NSAID use may slow healing in patients with active wounds "
            "or at elevated risk of skin breakdown.\n\n"
            "**Suggested action:** if this patient has or is at risk of pressure injury, "
            "consider adding a Company® prophylactic dressing (e.g. Dressing B) "
            "at bony prominences to reduce friction and shear while healing may be impaired.\n\n"
            "This card is informational — no action is required if wound risk has already "
            "been assessed."
        ),
        indicator="warning",
        source=CdsSource(**_COMPANY_SOURCE),
        suggestions=[
            CdsSuggestion(
                label="Add prophylactic Dressing B dressing order",
                uuid="suggestion-nsaid-dressing-001",
                isRecommended=False,
                actions=[
                    CdsAction(
                        type="create",
                        description="Create prophylactic wound dressing ServiceRequest",
                        resource={
                            "resourceType": "ServiceRequest",
                            "status": "draft",
                            "intent": "order",
                            "priority": "routine",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://snomed.info/sct",
                                        "code": "225130001",
                                        "display": "Application of dressing to wound",
                                    }
                                ],
                                "text": "Prophylactic Dressing B dressing — bony prominences",
                            },
                            "subject": {"reference": f"Patient/{patient_id}"},
                            "patientInstruction": (
                                "Apply Dressing B self-adherent foam dressing over "
                                "sacrum and/or heels. Inspect daily. Replace every 3–5 days "
                                "or sooner if integrity is compromised."
                            ),
                        },
                    )
                ],
            )
        ],
        selectionBehavior="at-most-one",
        links=[
            CdsLink(
                label="NSAIDs and wound healing — clinical reference",
                url="https://www.company.com/en-us/wound-care-academy/",
                type="absolute",
            )
        ],
    )


def _wound_care_confirmation_card(patient_id: str) -> CdsCard:
    return CdsCard(
        uuid="wound-care-order-sign-confirm-001",
        summary="Wound care order being signed — confirm dressing selection",
        detail=(
            "A wound care order is about to be committed. Before signing, confirm:\n\n"
            "- **Dressing type** matches wound depth and exudate level:\n"
            "  - Superficial / low exudate → **Dressing C** (wound contact layer)\n"
            "  - Moderate exudate → **Dressing T** (thin absorbent)\n"
            "  - Pressure injury stage 2–3, heel/sacrum → **Dressing B** (bordered foam)\n"
            "- **Change frequency** is documented (typically every 3 days for foam dressings)\n"
            "- **Wound assessment** at each change is included in the care plan\n\n"
            "No action required if the protocol is already complete."
        ),
        indicator="info",
        source=CdsSource(**_COMPANY_SOURCE),
        links=[
            CdsLink(
                label="Company® Dressing Selection Guide",
                url="https://www.company.com/en-us/products/wound-care/",
                type="absolute",
            )
        ],
    )

