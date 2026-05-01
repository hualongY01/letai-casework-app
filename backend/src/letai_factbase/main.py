from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from letai_factbase.api.routes import router
from letai_factbase.db.session import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="Letai Factbase",
        version="0.1.0",
        description="Local source-grounded factbase for Letai casework.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    init_db()
    return app


app = create_app()
