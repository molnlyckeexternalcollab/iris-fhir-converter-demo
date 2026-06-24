"""IOP message types for CDS Hooks interop flow.

These are the message classes exchanged between the CDS BS → BP → BO
components.

IOP constraint: PydanticMessage subclasses must NOT have an @dataclass
decorator.  IOP serialises them via model_dump_json()/model_validate_json().

Design note — two-context import split:
  WSGI workers load modules as `routers.*` (IRIS adds CDS/ to sys.path).
  The IRIS production loads modules as `CDS.routers.*` (only src/CDS/python
  on sys.path via PYTHONPATH).  The same source file would be two different
  Python module objects and therefore two different class objects — Pydantic
  would reject instances of one as "not an instance of" the other.
  Solution: use Any for the hook payload fields.  IOP serialises via JSON
  so class identity is irrelevant across the BS→BP boundary.  Each side
  reconstructs the typed model after deserialization using its own import path.
"""

from typing import Any, Optional

from iop import PydanticMessage

# No imports from routers.* or CDS.routers.* — this module is imported by
# both the WSGI context (BS) and the production context (BP/BO) and must
# remain neutral.


# ---------------------------------------------------------------------------
# patient-view
# ---------------------------------------------------------------------------

class PatientViewInputRequest(PydanticMessage):
    """Carries the patient-view CDS Hooks request across the BS→BP boundary.

    ``input`` is typed as Any so that Pydantic does not enforce class identity
    across the two import contexts.  The BS passes a PatientViewHookInput
    instance; IOP serialises it to JSON; the BP deserialises as a dict and
    reconstructs PatientViewHookInput via model_validate().
    """
    input: Any


class PatientViewResponse(PydanticMessage):
    """Carries the patient-view CDS Hooks response across the BP→BS boundary."""
    response: Any


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
