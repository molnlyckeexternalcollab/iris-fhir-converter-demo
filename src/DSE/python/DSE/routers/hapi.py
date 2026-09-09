import traceback
from typing import Any

from DSE.interop.bs.hapi import get_bs
from fastapi import APIRouter, HTTPException
from DSE.models import RiskAssessmentInput, RiskCalculationResult

router = APIRouter(tags=["DSE"])

@router.post("/hapi", response_model=RiskCalculationResult)
async def calculate_hapi_risk(body: RiskAssessmentInput):
    try:
        # BS.on_process_input already unwraps the BP response and returns a RiskCalculationResult directly
        rsp: RiskCalculationResult = get_bs().on_process_input(body)
        return rsp
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@router.post("/hapi/from-bundle", response_model=RiskCalculationResult)
async def calculate_hapi_risk_from_bundle(body: dict[str, Any]):
    """Same calculation as /hapi, but inputs are extracted from an already-fetched FHIR Bundle."""
    try:
        rsp: RiskCalculationResult = get_bs().on_process_bundle_input(body)
        return rsp
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

