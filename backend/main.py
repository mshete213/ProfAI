from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth as auth_routes
from api.routes import chat as chat_routes
from api.routes import courses as course_routes
from api.routes import ingestion as ingestion_routes
from api.routes import webhooks as webhook_routes
from config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="EdTech RAG Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_public_url, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(auth_routes.users_router)
app.include_router(course_routes.router)
app.include_router(ingestion_routes.router)
app.include_router(chat_routes.router)
app.include_router(webhook_routes.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"name": "EdTech RAG Platform", "version": "0.1.0"}
