"""IOP message types for CDS Hooks interop flow.

These are the message classes exchanged between the CDS BS → BP → BO
components.  They wrap the Pydantic models from the CDS router layer so
that the business logic can reason in FHIR/CDS terms rather than raw dicts.

IOP constraint: PydanticMessage subclasses must NOT have an @dataclass
decorator.  IOP serialises them via model_dump_json()/model_validate_json().
"""

from typing import Any, Optional

from iop import PydanticMessage

from CDS.routers.cds_hooks_models import CdsHookRequest, CdsHookResponse


# ---------------------------------------------------------------------------
# patient-view
# ---------------------------------------------------------------------------

class PatientViewRequest(PydanticMessage):
    """Wraps the inbound CDS Hooks request for the patient-view hook."""
    request: CdsHookRequest


class PatientViewResponse(PydanticMessage):
    """Wraps the outbound CDS Hooks response for the patient-view hook."""
    response: CdsHookResponse


# ---------------------------------------------------------------------------
# order-select
# ---------------------------------------------------------------------------

class OrderSelectRequest(PydanticMessage):
    """Wraps the inbound CDS Hooks request for the order-select hook."""
    request: CdsHookRequest


class OrderSelectResponse(PydanticMessage):
    """Wraps the outbound CDS Hooks response for the order-select hook."""
    response: CdsHookResponse


# ---------------------------------------------------------------------------
# order-sign
# ---------------------------------------------------------------------------

class OrderSignRequest(PydanticMessage):
    """Wraps the inbound CDS Hooks request for the order-sign hook."""
    request: CdsHookRequest


class OrderSignResponse(PydanticMessage):
    """Wraps the outbound CDS Hooks response for the order-sign hook."""
    response: CdsHookResponse


# ---------------------------------------------------------------------------
# FHIR read (used by BO.Fhir)
# ---------------------------------------------------------------------------

class FhirReadRequest(PydanticMessage):
    """Request a single FHIR resource from the EHR FHIR server."""
    fhir_server: str
    resource_type: str
    resource_id: str
    token: Optional[str] = None


class FhirReadResponse(PydanticMessage):
    """Wraps the raw FHIR resource JSON returned by BO.Fhir."""
    resource: dict[str, Any]
