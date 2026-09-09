"""IOP message classes for the DSE IRIS production.

HAPI risk assessment messages
"""

from typing import Any

from iop import PydanticMessage

from DSE.models import RiskAssessmentInput, RiskCalculationResult

# No @dataclass decorator: IOP's _serialization.py explicitly raises SerializationError
# when a class combines @dataclass with PydanticMessage (a BaseModel subclass).
# Serialization is handled via model_dump_json()/model_validate_json() — no dataclass needed.

class RiskAssessmentInputRequest(PydanticMessage):
    input: RiskAssessmentInput


class RiskAssessmentBundleRequest(PydanticMessage):
    """Carries an already-fetched FHIR Bundle (or single resource) to extract inputs from."""
    bundle: dict[str, Any]


class RiskAssessmentResultResponse(PydanticMessage):
    result: RiskCalculationResult
