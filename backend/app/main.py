from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from starlette.exceptions import HTTPException as StarletteHTTPException

from .routers import ocr, export, corrections

app = FastAPI(title="OCR Web Application", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API routes (matched first) ---
app.include_router(ocr.router)
app.include_router(export.router)
app.include_router(corrections.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# --- Static file mounts ---
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Serve React frontend build (must be LAST mount)
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIR.exists():
    # html=True serves index.html for directory requests (SPA entrypoint)
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="spa")


# SPA fallback: any 404 on non-API routes serves index.html
@app.exception_handler(StarletteHTTPException)
async def spa_fallback(request, exc):
    if exc.status_code == 404 and not request.url.path.startswith("/api"):
        index = FRONTEND_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
    from fastapi.responses import JSONResponse
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
