from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
from database import SessionLocal
from models import User

router = APIRouter(prefix="/auth")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthRequest(BaseModel):
    username: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
def register(req: AuthRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == req.username).first()
        if user:
            raise HTTPException(status_code=400, detail="User already exists")

        new_user = User(
            username=req.username,
            password=pwd_context.hash(req.password)
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "Success", "user_id": new_user.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/login")
def login(req: AuthRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == req.username).first()
        if not user or not pwd_context.verify(req.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {"message": "Login successful", "user_id": user.id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")
