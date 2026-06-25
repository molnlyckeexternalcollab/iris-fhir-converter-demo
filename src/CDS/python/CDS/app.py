import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from CDS.routers.hapi import router as hapi_router
from CDS.routers.cds_services import router as cds_services_router
from CDS.routers.patient_view import router as patient_view_router
from CDS.routers.order_select import router as order_select_router
from CDS.routers.order_sign import router as order_sign_router

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

app = FastAPI(
    title="CDS Service",
    description="Mock EHR/integration APIs for EMIL POC",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    """Return a plain text response with the traceback for debugging.
    
    TODO: This is useful for development and debugging, but should not be used in production.
    """
    return PlainTextResponse(traceback.format_exc(), status_code=500)

app.include_router(hapi_router)
app.include_router(cds_services_router)
app.include_router(patient_view_router)
app.include_router(order_select_router)
app.include_router(order_sign_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
