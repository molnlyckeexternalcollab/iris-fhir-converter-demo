import traceback
from CDS.interop.bs.hapi import get_bs
from fastapi import APIRouter, HTTPException
from CDS.models import RiskAssessmentInput, RiskCalculationResult

router = APIRouter(tags=["HAC PI Risk Calculator"])

@router.post("/hapi", response_model=RiskCalculationResult)
async def calculate_hapi_risk(body: RiskAssessmentInput):
    try:
        # BS.on_process_input already unwraps the BP response and returns a RiskCalculationResult directly
        rsp: RiskCalculationResult = get_bs().on_process_input(body)
        return rsp
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())
