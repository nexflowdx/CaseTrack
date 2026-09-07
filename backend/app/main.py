from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.services.auth import get_current_employee
from app.routes.incidents import router as incidents_router

app = FastAPI(title="CaseTrack API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(incidents_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/whoami")
async def whoami(employee: dict = Depends(get_current_employee)):
    return employee