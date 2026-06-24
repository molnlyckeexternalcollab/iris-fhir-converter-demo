"""Business Service — HAPI risk calculator endpoint."""

from iop import BusinessService, Director
from CDS.interop.msg import RiskAssessmentInputRequest, RiskAssessmentResultResponse
from CDS.models import RiskAssessmentInput, RiskCalculationResult

# Lazy: do NOT call Director at module level — the portal imports this file
# for validation before any production is started, which could cause an error.
_bs = None


def get_bs():
    global _bs
    if _bs is None:
        _bs = Director.create_python_business_service('BS.Hapi')
    return _bs


class Hapi(BusinessService):
    def on_process_input(self, message_input: RiskAssessmentInput) -> RiskCalculationResult:
        msg = RiskAssessmentInputRequest(input=message_input)
        response: RiskAssessmentResultResponse = self.send_request_sync('BP.Hapi', msg)
        return response.result
