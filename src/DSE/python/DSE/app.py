import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from DSE.routers.hapi import router as hapi_router

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# asyncio logs "Using selector: EpollSelector" at DEBUG level to stdout.
# Under IRIS WSGI, stdout is captured as part of the HTTP response body,
# which corrupts JSON responses. Suppress asyncio debug noise.
logging.getLogger("asyncio").setLevel(logging.WARNING)

app = FastAPI(
    title="DSE Service",
    description="Decision Support Engine",
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8002)
