from fastapi import FastAPI

from app.api.alerts import router as alerts_router
from app.api.benchmarks import router as benchmarks_router
from app.api.models import router as models_router
from app.api.monitoring import router as monitoring_router
from app.api.providers import router as providers_router

app = FastAPI(title="LLM Performance Monitor", version="0.1.0")

# Register API routers
app.include_router(alerts_router)
app.include_router(benchmarks_router)
app.include_router(models_router)
app.include_router(monitoring_router)
app.include_router(providers_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
