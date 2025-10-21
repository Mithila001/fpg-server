from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine
from app.db.base import init_db
from app.routers import user, layout
from backend.app.routers import dimensions

app = FastAPI(title="House Plan Generator API")

# dev-safe CORS — restrict to your frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db(engine)

app.include_router(layout.router)
app.include_router(user.router, prefix="/users", tags=["users"])
app.include_router(dimensions.router)
