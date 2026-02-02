from fastapi import FastAPI

app = FastAPI(title="LLM Performance Monitor", version="0.1.0")


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
