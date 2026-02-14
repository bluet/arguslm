from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arguslm.server.api.alerts import router as alerts_router
from arguslm.server.api.benchmarks import router as benchmarks_router
from arguslm.server.api.models import router as models_router
from arguslm.server.api.monitoring import router as monitoring_router
from arguslm.server.api.providers import router as providers_router
from arguslm.server.core.config import get_settings
from arguslm.server.core.scheduler import start_scheduler, stop_scheduler
from arguslm.server.db.init import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_scheduler()
    yield
    await stop_scheduler()


app = FastAPI(title="LLM Performance Monitor", version="0.1.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
