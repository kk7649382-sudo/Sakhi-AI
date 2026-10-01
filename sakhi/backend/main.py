"""
Main ASGI application for Sakhi (சகி) - Tamil Government Scheme Voice & Web Assistant.
Built using Starlette for high-performance, lightweight, production-ready serving.
"""

import os
import json
from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, FileResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from .scheme_catalog import get_default_scheme, get_scheme_by_id, list_available_schemes
from .ai_service import SakhiAIService
from .tts_service import generate_tamil_audio

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# Global AI service instance
ai_service = SakhiAIService()


async def health_check(request: Request) -> JSONResponse:
    """System health check and feature capability report."""
    has_gemini = bool(os.environ.get("GEMINI_API_KEY", "") or ai_service.api_key)
    return JSONResponse({
        "status": "healthy",
        "app_name": "Sakhi (சகி)",
        "version": "1.0.0",
        "primary_language": "ta",
        "gemini_active": has_gemini,
        "tts_available": True,
        "default_scheme": "kmut"
    })


async def get_schemes_list(request: Request) -> JSONResponse:
    """Return all supported government schemes."""
    schemes = list_available_schemes()
    return JSONResponse({"schemes": schemes})


async def get_scheme_details(request: Request) -> JSONResponse:
    """Return full details for requested scheme ID or default scheme."""
    scheme_id = request.path_params.get("scheme_id", "kmut")
    scheme = get_scheme_by_id(scheme_id) or get_default_scheme()
    return JSONResponse({"scheme": scheme})


async def chat_endpoint(request: Request) -> JSONResponse:
    """
    Process conversational query in Tamil.
    Grounded strictly on verified scheme information with fallback.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    user_query = body.get("query", "").strip()
    user_api_key = body.get("api_key", "").strip()

    # If user provided a custom API key in settings, create/use instance with it
    service = ai_service
    if user_api_key and user_api_key != ai_service.api_key:
        service = SakhiAIService(api_key=user_api_key)

    response_data = await service.answer_query(user_query)
    return JSONResponse(response_data)


async def tts_endpoint(request: Request) -> Response:
    """
    Generate and stream spoken Tamil audio (MP3) for given text.
    """
    text = request.query_params.get("text", "").strip()
    slow_param = request.query_params.get("slow", "0")
    slow = slow_param in ("1", "true", "True")

    if not text:
        text = "வணக்கம் அக்கா, நான் சகி."

    try:
        audio_bytes = generate_tamil_audio(text, slow=slow)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Content-Disposition": "inline; filename=sakhi_speech.mp3"
            }
        )
    except Exception as e:
        return JSONResponse({"error": f"Audio generation failed: {str(e)}"}, status_code=500)


async def index(request: Request):
    """Serve mobile-first SPA homepage."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"error": "Frontend static files not found"}, status_code=404)


# Route definitions
routes = [
    Route("/", endpoint=index, methods=["GET"]),
    Route("/api/health", endpoint=health_check, methods=["GET"]),
    Route("/api/schemes", endpoint=get_schemes_list, methods=["GET"]),
    Route("/api/scheme/{scheme_id}", endpoint=get_scheme_details, methods=["GET"]),
    Route("/api/chat", endpoint=chat_endpoint, methods=["POST"]),
    Route("/api/tts", endpoint=tts_endpoint, methods=["GET"]),
    Mount("/static", app=StaticFiles(directory=str(STATIC_DIR)), name="static"),
]

# CORS middleware to allow local testing and mobile web views
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"]
    )
]

app = Starlette(routes=routes, middleware=middleware)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"🌸 Starting Sakhi server on http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
