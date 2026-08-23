"""Smart Resume Screener — FastAPI application entry point."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router
from app.core.config import get_settings
from app.core.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

settings = get_settings()

app = FastAPI(
    title="Smart Resume Screener API",
    version="1.0.0",
    description=(
        "Parses resumes, extracts structured candidate information and matches "
        "candidates against job descriptions using an LLM with explainable "
        "1-10 scoring."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info(
        "Smart Resume Screener started | db=%s | llm=%s",
        settings.database_url.split("://", 1)[0],
        settings.llm_provider,
    )


# ---------------------------------------------------------------------------
# Consistent error envelope; internal details are never leaked to clients.
# ---------------------------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": str(exc.detail), "status": exc.status_code}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Validation failed for the request.",
                "details": [
                    {
                        "field": ".".join(str(loc) for loc in err.get("loc", [])[1:]),
                        "issue": err.get("msg", ""),
                    }
                    for err in exc.errors()
                ][:10],
                "status": 422,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error.",
                "status": 500,
            }
        },
    )


app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"name": "Smart Resume Screener API", "docs": "/api/docs"}
