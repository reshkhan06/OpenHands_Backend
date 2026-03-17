from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import uvicorn
from app.api.user import router as user_route
from app.api.ngo import router as ngo_route
from app.api.pickups import router as pickups_route
from app.api.payments import router as payments_route
from app.api.admin import router as admin_route
from app.api.verify import router as verify_route
from app.api.feedback import router as feedback_route
from app.db.connection import create_db_and_tables


app = FastAPI()

# Serve uploaded files (certificates, etc.)
uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create database tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def home():
    return {"message": "Server is running for Donation OpenHand"}


# include router
app.include_router(user_route, prefix="/user", tags=["User Authentication"])
app.include_router(ngo_route, prefix="/ngo", tags=["NGO Registration"])
app.include_router(pickups_route, prefix="/pickups", tags=["Pickups"])
app.include_router(payments_route, prefix="/payments", tags=["Payments"])
app.include_router(admin_route)
app.include_router(verify_route, tags=["Verification"])
app.include_router(feedback_route, prefix="/feedback", tags=["Feedback"])

if __name__ == "__main__":
    uvicorn.run(app, port=8000, reload=True)
