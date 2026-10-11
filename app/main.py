import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import get_stats, init_db, list_tickets, save_ticket
from app.llm_client import LLMError, triage
from app.rate_limit import RateLimiter
from app.schemas import TriageRequest, TriageResponse

# Frontend is a separate top-level module (../frontend), not part of the
# backend package — the API doesn't know or care who consumes it.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("helpdesk")

limiter = RateLimiter(limit_per_minute=settings.rate_limit_per_minute)

FALLBACK_REPLY = "Ваше обращение передано оператору. Мы ответим вам в ближайшее время."


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Helpdesk Triage MVP", lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/triage", response_model=TriageResponse)
def triage_endpoint(payload: TriageRequest) -> TriageResponse:
    if not limiter.allow(payload.client_id):
        raise HTTPException(
            status_code=429,
            detail=f"Слишком много запросов. Лимит: {settings.rate_limit_per_minute}/мин на client_id.",
        )

    error: str | None = None
    try:
        result = triage(payload.text)
    except LLMError as exc:
        logger.error("LLM failure for client_id=%s: %s", payload.client_id, exc)
        error = str(exc)
        result = TriageResponse(
            category="other",
            draft_reply=FALLBACK_REPLY,
            confidence="low",
            escalate=True,
        )

    save_ticket(
        client_id=payload.client_id,
        channel=payload.channel,
        text=payload.text,
        category=result.category,
        confidence=result.confidence,
        escalate=result.escalate,
        draft_reply=result.draft_reply,
        error=error,
    )

    return result


@app.get("/tickets")
def tickets(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: str | None = None,
    confidence: str | None = None,
    escalate: bool | None = None,
    channel: str | None = None,
    q: str | None = None,
    only_errors: bool = False,
) -> dict:
    items, total = list_tickets(
        limit=limit,
        offset=offset,
        category=category,
        confidence=confidence,
        escalate=escalate,
        channel=channel,
        q=q,
        only_errors=only_errors,
    )
    return {"items": items, "total": total}


@app.get("/stats")
def stats() -> dict:
    return get_stats()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
