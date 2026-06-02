from fastapi import FastAPI
from routers.hapi import router as hapi_router
from routers.cds_services import router as cds_services_router

app = FastAPI(
    title="CDS Service",
    description="Mock EHR/integration APIs for EMIL POC",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(hapi_router)
app.include_router(cds_services_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
