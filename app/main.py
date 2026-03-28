# uvicorn app.main:app --reload

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="House Plan Generator API")


# create database tables before serving
@app.on_event("startup")
def on_startup():
    from app.core import database

    database.create_db_and_tables()


# dev-safe CORS — restrict to your frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Algorithm routers

# include the algorithm-related endpoints we just added
from app.routes.routes import router as algorithms_router  # noqa: E402

app.include_router(algorithms_router)
