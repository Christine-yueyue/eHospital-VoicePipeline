"""FastAPI backend for the Flutter voice demo. Run: uvicorn app:app --reload"""

import os
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from services import LANGUAGES, check_target, transcribe_audio, translate_text
from live import live_router
from auth import app_token, authorized
import whatsapp

ALLOWED_EXTENSIONS = {".ogg", ".opus", ".mp3", ".wav", ".m4a", ".webm"}
try:
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
    if not 1 <= MAX_UPLOAD_MB <= 25:
        raise ValueError
except ValueError:
    raise RuntimeError("MAX_UPLOAD_MB must be a whole number from 1 to 25.") from None
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1_000_000
DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8003,http://127.0.0.1:8003"

@asynccontextmanager
async def lifespan(_app):
    task = asyncio.create_task(whatsapp.worker())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Voice Notes v3 — iOS & WhatsApp", lifespan=lifespan)


@app.middleware("http")
async def protect_api(request: Request, call_next):
    if request.url.path.startswith('/api/') and request.method != 'OPTIONS':
        if not app_token():
            return JSONResponse(status_code=503, content={'success': False, 'error': 'Set APP_ACCESS_TOKEN in the backend .env file.'})
        if not authorized(request.headers.get('authorization', '')):
            return JSONResponse(status_code=401, content={'success': False, 'error': 'Enter the correct app access token in Connection settings.'}, headers={'WWW-Authenticate': 'Bearer'})
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[v.strip() for v in os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")],
    allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"],
)
app.include_router(live_router)
app.include_router(whatsapp.router)


@app.exception_handler(StarletteHTTPException)
async def http_error(_request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, _exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"success": False, "error": "Check the audio file and target language."})


@app.get("/api/config")
async def config():
    return {"max_upload_bytes": MAX_UPLOAD_BYTES, "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
            "languages": LANGUAGES, "live_sample_rate": 24000, "version": "3.0.0",
            "whatsapp": whatsapp.settings()}


@app.get('/health')
async def health():
    return {'status': 'ok', 'version': '3.0.0'}


@app.post("/api/transcribe")
async def transcribe(file: UploadFile | None = File(default=None), target_language: str = Form("")):
    """Keep the original endpoint; translation is optional for older clients."""
    try:
        if target_language:
            check_target(target_language)
        if file is None or not file.filename:
            raise HTTPException(400, "Please select an audio file.")
        filename = Path(file.filename.replace("\\", "/")).name
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, "Choose an .ogg, .opus, .mp3, .wav, .m4a, or .webm audio file.")
        if file.size is not None and file.size > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"File too large. Maximum size: {MAX_UPLOAD_MB} MB.")
        with TemporaryDirectory(prefix="voice-upload-") as directory:
            path = Path(directory) / f"audio{extension}"
            size = 0
            with path.open("wb") as output:
                while chunk := await file.read(64 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, f"File too large. Maximum size: {MAX_UPLOAD_MB} MB.")
                    output.write(chunk)
            if not size:
                raise HTTPException(400, "The audio file is empty.")
            transcript = await transcribe_audio(str(path))
        result = {"success": True, "filename": filename, "transcript": transcript,
                  "translation": "", "target_language": target_language}
        if target_language:
            try:
                result["translation"] = await translate_text(transcript, target_language)
            except HTTPException as exc:
                # A translation outage should not discard a successful transcript.
                result["translation_error"] = str(exc.detail)
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "Processing failed. Please try again.") from None
    finally:
        if file is not None:
            await file.close()


# Serve the compiled Flutter app after `flutter build web`. API routes come first.
WEB_BUILD = BASE_DIR.parent / "frontend" / "build" / "web"
if WEB_BUILD.is_dir():
    app.mount("/", StaticFiles(directory=WEB_BUILD, html=True), name="flutter")
else:
    @app.get("/")
    async def index():
        return {"message": "Backend ready. Run Flutter on http://localhost:5173. See README.md.", "docs": "/docs"}
