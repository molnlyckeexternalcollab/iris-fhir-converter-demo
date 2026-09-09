"""Business Service — HAPI risk calculator endpoint."""

from typing import Any

from iop import BusinessService, Director, target
from DSE.interop.msg import RiskAssessmentBundleRequest, RiskAssessmentInputRequest, RiskAssessmentResultResponse
from DSE.models import RiskAssessmentInput, RiskCalculationResult

# Lazy: do NOT call Director at module level — the portal imports this file
# for validation before any production is started, which could cause an error.
_bs = None


def get_bs():
    global _bs
    if _bs is None:
        _bs = Director.create_python_business_service('BS.Hapi')
    return _bs


class Hapi(BusinessService):
    
    process_target = target('Process') 

    def on_process_input(self, message_input: RiskAssessmentInput) -> RiskCalculationResult:
        msg = RiskAssessmentInputRequest(input=message_input)
        response: RiskAssessmentResultResponse = self.send_request_sync(self.process_target, msg)
        return response.result

    def on_process_bundle_input(self, bundle: dict[str, Any]) -> RiskCalculationResult:
        """Same as on_process_input, but the input is extracted from a FHIR Bundle."""
        msg = RiskAssessmentBundleRequest(bundle=bundle)
        response: RiskAssessmentResultResponse = self.send_request_sync(self.process_target, msg)
        return response.result
