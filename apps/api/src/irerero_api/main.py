from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from irerero_api.config import get_settings
from irerero_api.routes import (
    admin,
    alerts,
    assistant,
    auth,
    brief,
    centres,
    demo,
    geo,
    national,
    parent,
    plan,
    public,
    reports,
    sms,
    system,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="IrereroAI API",
        version="0.1.0",
        description="Decision support for early childhood development in Rwanda. "
        "Suggestions only: every action needs a person's approval.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (
        system,
        auth,
        demo,
        public,
        parent,
        reports,
        sms,
        centres,
        geo,
        plan,
        brief,
        national,
        admin,
        assistant,
        alerts,
    ):
        app.include_router(module.router)
    app.include_router(alerts.officers)
    return app


app = create_app()
