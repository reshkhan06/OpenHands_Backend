from fastapi import FastAPI
import uvicorn
from app.api.user import router as user_route
from app.db.connection import create_db_and_tables


app = FastAPI()


# Create database tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def home():
    return {"message": "Server is running for Donation OpenHand"}


# include router
app.include_router(user_route, prefix="/user")

if __name__ == "__main__":
    uvicorn.run(app, port=8000, reload=True)
