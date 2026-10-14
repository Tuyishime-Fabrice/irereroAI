from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from irerero_api.config import get_settings
from irerero_api.routes import auth, brief, demo, geo, national, plan, public, system


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="IrereroAI API",
        version="0.1.0",
        description="AI planning layer for early childhood development in Rwanda: where to build, "
        "upgrade or support ECD centres for a budget. Suggestions only: every action needs a "
        "planner's approval.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (system, auth, demo, public, geo, plan, brief, national):
        app.include_router(module.router)
    return app


app = create_app()
