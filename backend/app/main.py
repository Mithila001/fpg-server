from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import user, layout
from app.routers import dimensions
from app.routers import fp_boundary, usable_land_space, floor_plan

app = FastAPI(title="House Plan Generator API")

# dev-safe CORS — restrict to your frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(layout.router)
app.include_router(user.router, prefix="/users", tags=["users"])
app.include_router(dimensions.router)

# Algorithm routers
app.include_router(fp_boundary.router)
app.include_router(usable_land_space.router)
app.include_router(floor_plan.router)
