from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import optimization, crra, portfolio, market_data

settings = get_settings()

app = FastAPI(
    title="Merton Portfolio Optimizer",
    description="Portfolio allocation using Merton's optimal portfolio theory",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    optimization.router,
    prefix=f"{settings.api_v1_prefix}/optimize",
    tags=["optimization"],
)
app.include_router(
    crra.router,
    prefix=f"{settings.api_v1_prefix}/crra",
    tags=["crra"],
)
app.include_router(
    portfolio.router,
    prefix=f"{settings.api_v1_prefix}/portfolio",
    tags=["portfolio"],
)
app.include_router(
    market_data.router,
    prefix=f"{settings.api_v1_prefix}/market-data",
    tags=["market-data"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
