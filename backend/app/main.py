"""FastAPI application factory. Run with: uvicorn app.main:app --reload"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="PropWise AI API",
        version="0.1.0",
        description="Property discovery, explainable recommendations, indicative price estimates and a grounded "
                    "assistant for Hubballi–Dharwad. Most demo listings are synthetic; a few are real third-party listings, labelled with their source.",
    )
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                       allow_headers=["Authorization", "Content-Type"])
    install_error_handlers(app)

    @app.middleware("http")
    async def _security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response

    app.include_router(api_router)
    # Listing photos only. Document files are never served from here.
    images_dir = Path(s.storage_dir) / "properties"
    images_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media/properties", StaticFiles(directory=images_dir), name="media")
    return app


app = create_app()
