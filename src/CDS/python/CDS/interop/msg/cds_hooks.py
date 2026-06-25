"""IOP message types for CDS Hooks interop flow.

These are the message classes exchanged between the CDS BS → BP → BO
components.

IOP constraint: PydanticMessage subclasses must NOT have an @dataclass
decorator.  IOP serialises them via model_dump_json()/model_validate_json().

Design note — why hook payload fields are typed Any:
  The WSGI worker (FastAPI) has CDS/ on sys.path, so it imports
  PatientViewHookInput as `routers.contexts.PatientViewHookInput`.
  The production worker has src/CDS/python on sys.path, so it imports the
  same class as `CDS.routers.contexts.PatientViewHookInput`.
  These are two different Python class objects.  If the fields were typed as
  PatientViewHookInput, IOP would reject instances from the WSGI context as
  "not an instance of" the production-context class.
  Typing as Any sidesteps this: IOP serialises the value to JSON regardless,
  and the receiving side reconstructs the typed model via model_validate().
"""

from typing import Any, Optional

from iop import PydanticMessage

from CDS.routers.contexts import PatientViewHookInput
from CDS.routers.cds_hooks_models import CdsHookResponse


# ---------------------------------------------------------------------------
# patient-view
# ---------------------------------------------------------------------------

class PatientViewInputRequest(PydanticMessage):
    """Carries the patient-view CDS Hooks request across the BS→BP boundary."""
    input: PatientViewHookInput


class PatientViewResponse(PydanticMessage):
    """Carries the patient-view CDS Hooks response across the BP→BS boundary."""
    response: CdsHookResponse


# ---------------------------------------------------------------------------
# order-select
# ---------------------------------------------------------------------------

class OrderSelectRequest(PydanticMessage):
    input: Any


class OrderSelectResponse(PydanticMessage):
    response: Any


# ---------------------------------------------------------------------------
# order-sign
# ---------------------------------------------------------------------------

class OrderSignRequest(PydanticMessage):
    input: Any


class OrderSignResponse(PydanticMessage):
    response: Any


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
