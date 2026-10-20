from fastapi import APIRouter

from app.api.v1.routes import admin, auth, chat, meta, predictions, properties, recommendations, system, users

api_router = APIRouter(prefix="/api/v1")
for r in (system.router, auth.router, users.router, meta.router, recommendations.router, properties.router,
          admin.router, predictions.router, chat.router):
    api_router.include_router(r)
