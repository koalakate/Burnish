from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.routers import brand, checks, corrections, decks

app = FastAPI(title="Burnish API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(decks.router)
app.include_router(checks.router)
app.include_router(corrections.router)
app.include_router(brand.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
