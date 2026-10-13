import json
import logging
import time
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from career_ai.core import match, pipeline
from career_ai.documents import DocumentError, extract_document
from career_ai.evidence import EXTRACTOR_VERSION, MAX_TEXT, TAXONOMY_VERSION, compare, extract_profile

logger = logging.getLogger("career_ai.requests")
MAX_REQUEST_BYTES = 6 * 1024 * 1024
STATIC = Path(__file__).parent / "static"


class LocalBoundary:
    """Cap body before JSON decoding; collect metrics without personal data."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started, status = time.perf_counter(), 500
        headers = dict(scope["headers"])

        async def private_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"content-security-policy", b"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")]
            await send(message)

        try:
            origin = headers.get(b"origin")
            if origin:
                try:
                    parsed = urlsplit(origin.decode("ascii"))
                    valid_origin = parsed.scheme in {"http", "https"} and parsed.netloc == headers.get(b"host", b"").decode("ascii")
                except (ValueError, UnicodeError):
                    valid_origin = False
                if not valid_origin:
                    return await JSONResponse({"detail": "Origen no permitido."}, status_code=403)(scope, receive, private_send)
            length = headers.get(b"content-length")
            if length:
                try:
                    declared = int(length)
                except ValueError:
                    declared = -1
                if declared < 0 or declared > MAX_REQUEST_BYTES:
                    return await JSONResponse({"detail": "Tamaño de solicitud no permitido."}, status_code=413)(scope, receive, private_send)
            chunks, size = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > MAX_REQUEST_BYTES:
                    return await JSONResponse({"detail": "La solicitud supera 6 MiB."}, status_code=413)(scope, receive, private_send)
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            body = b"".join(chunks)
            delivered = False

            async def replay():
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}

            await self.app(scope, replay, private_send)
        finally:
            route = scope.get("route")
            logger.info(json.dumps({"event": "request", "route": getattr(route, "path", "/unknown"),
                                    "method": scope["method"], "status": status,
                                    "latency_ms": round((time.perf_counter() - started) * 1000, 2)}))


app = FastAPI(title="Career Intelligence AI", version="0.3.0", docs_url=None, redoc_url=None)
app.add_middleware(LocalBoundary)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])
app.mount("/static", StaticFiles(directory=STATIC, check_dir=False), name="static")


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Job(Contract):
    title: str = Field(min_length=1, max_length=500)
    company: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=50000)
    source_url: str = Field(default="", max_length=2000)


class AnalysisRequest(Contract):
    jobs: list[Job] = Field(max_length=500)
    profile_skills: list[str] = Field(max_length=100)


class ProfileRequest(Contract):
    text: str = Field(min_length=1, max_length=MAX_TEXT)


class ComparisonRequest(Contract):
    cv_text: str = Field(min_length=1, max_length=MAX_TEXT)
    vacancy_text: str = Field(min_length=1, max_length=50000)
    selected_skills: list[str] | None = Field(default=None, max_length=100)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Normal validation errors include the rejected input, potentially an entire CV.
    return JSONResponse(status_code=422, content={"detail": "Solicitud inválida. Revisa los campos y sus límites.",
                                                 "errors": [{"loc": error["loc"], "type": error["type"]}
                                                            for error in exc.errors()]})


@app.exception_handler(DocumentError)
async def document_error(request, exc):
    return JSONResponse(status_code=exc.status, content={"code": exc.code, "detail": str(exc)})


@app.get("/")
def home():
    if not (STATIC / "index.html").is_file():
        return JSONResponse(status_code=503, content={"detail": "Compila el frontend con npm ci y npm run build desde frontend/."})
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "extractor_version": EXTRACTOR_VERSION, "taxonomy_version": TAXONOMY_VERSION}


@app.post("/documents/extract")
async def extract(request: Request):
    document_format = request.headers.get("x-document-format", "")
    # Raw bytes avoid multipart spool files and keep the original filename private.
    result = await run_in_threadpool(extract_document, await request.body(), document_format)
    try:
        profile = await run_in_threadpool(extract_profile, result["text"])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    profile["warnings"] += result["warnings"]
    profile["document_format"] = result["format"]
    return profile


@app.post("/profile/review")
def review(request: ProfileRequest):
    try:
        return extract_profile(request.text)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post("/compare")
def comparison(request: ComparisonRequest):
    try:
        return compare(request.cv_text, request.vacancy_text, request.selected_skills)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post("/analyze")
def analyze(request: AnalysisRequest):
    """Legacy corpus analysis; keyword coverage differs from reviewed CV matching."""
    result = pipeline([job.model_dump() for job in request.jobs])
    for job in result["jobs"]:
        job["match"] = match(job, request.profile_skills)
    return result
