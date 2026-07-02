"""Business Operation — DSE HAPI risk calculator HTTP client.

Bridges the CDS production to the DSE namespace's HAPI risk endpoint over HTTP.
Keeping this class inside CDS/interop/ means iop can register it with the
correct Python class path (CDS/interop/). Cross-namespace class imports in
production.py are not supported: iop ties each proxy class's load path to the
directory containing settings.py.
"""

import json

import requests
from iop import BusinessOperation

from DSE.interop.msg import RiskAssessmentInputRequest, RiskAssessmentResultResponse
from DSE.models import RiskCalculationResult


class HttpOperation(BusinessOperation):
    """Posts a RiskAssessmentInput to the DSE HAPI endpoint and returns the result."""

    url: str = "http://localhost:52773/dse/hapi"

    def on_risk_assessment_input_request(
        self, request: RiskAssessmentInputRequest
    ) -> RiskAssessmentResultResponse:
        response = requests.post(
            self.url,
            json=json.loads(request.input.model_dump_json()),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        result = RiskCalculationResult.model_validate(response.json())
        return RiskAssessmentResultResponse(result=result)
