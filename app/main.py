# uvicorn main:app --reload --port 8010
# public (listen on all network instances):
# uvicorn main:app --reload --host 0.0.0.0 --port 8010
# testing on:
#   - Swagger: http://localhost:8010/docs
#   - Redoc: http://localhost:8010/redoc

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health
from app.routers import auth
from app.routers import query


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

    return app


app = create_app()
