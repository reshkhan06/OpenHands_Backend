from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api.user import router as user_route
from app.db.connection import create_db_and_tables


app = FastAPI()

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

if __name__ == "__main__":
    uvicorn.run(app, port=8000, reload=True)
