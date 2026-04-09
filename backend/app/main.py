from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import documents, approvals
from . import models, utils

app = FastAPI(title="Document Management System")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

# Include all routers
app.include_router(documents.router)
app.include_router(approvals.router)

# Root endpoint
@app.get("/")
def root():
    return {"message": "✅ Document Management System Backend is running!"}

# ====================== AUTHENTICATION ======================
from . import schemas, crud, auth
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db=Depends(crud.get_db_from_auth)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(crud.get_db_from_auth)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(current_user=Depends(auth.get_current_user)):
    return current_user

# ====================== REPORTS & INSIGHTS ======================

@app.get("/reports")
def get_reports(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(crud.get_db_from_auth)
):
    """Get spending report data"""
    report_data = crud.generate_report_data(db)
    return report_data

@app.get("/reports/insights")
async def get_insights(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(crud.get_db_from_auth)
):
    """Generate AI-powered spending insights"""
    report_data = crud.generate_report_data(db)
    insights = await utils.generate_spending_insights(report_data)
    return {"insights": insights}