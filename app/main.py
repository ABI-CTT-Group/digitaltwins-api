# uvicorn app.main:app --reload --port 8010
# public (listen on all network instances):
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
# API docs:
#   - Swagger: http://localhost:8010/docs
#   - Redoc: http://localhost:8010/redoc

import starlette.requests

# Raise the multipart upload limit (default is 1000 files / 1000 fields).
_original_form = starlette.requests.Request.form


def _patched_form(self, *, max_files=10_000, max_fields=10_000, max_part_size=1024 * 1024):
    return _original_form(self, max_files=max_files, max_fields=max_fields, max_part_size=max_part_size)


starlette.requests.Request.form = _patched_form  # type: ignore[method-assign]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import health, auth, query, upload, delete, download

def initialise(app):
    origins = [
        # "http://localhost:3000",
        # "http://127.0.0.1:3000",
        # Add other allowed origins here
        "*",  # allow all origins (use carefully in production)
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # origins allowed to make cross-origin requests
        allow_credentials=True,
        allow_methods=["*"],  # allow all HTTP methods (GET, POST, etc.)
        allow_headers=["*"],  # allow all headers
    )

    return app


def create_app() -> FastAPI:
    app = FastAPI()

    # initialise app settings
    app = initialise(app)

    # include routers
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(query.router)
    app.include_router(upload.router)
    app.include_router(delete.router)
    app.include_router(download.router)

    return app


app = create_app()
