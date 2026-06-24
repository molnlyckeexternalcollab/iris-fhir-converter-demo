"""IOP message classes for the CDS IRIS production.

Sub-modules:
  msg.cds_hooks  — messages for the CDS Hooks BS/BP flow
  (this module)  — legacy HAPI risk assessment messages
"""

from iop import PydanticMessage

from CDS.models import RiskAssessmentInput, RiskCalculationResult

# No @dataclass decorator: IOP's _serialization.py explicitly raises SerializationError
# when a class combines @dataclass with PydanticMessage (a BaseModel subclass).
# Serialization is handled via model_dump_json()/model_validate_json() — no dataclass needed.

class RiskAssessmentInputRequest(PydanticMessage):
    input: RiskAssessmentInput


class RiskAssessmentResultResponse(PydanticMessage):
    result: RiskCalculationResult
