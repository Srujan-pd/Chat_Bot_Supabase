from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Chat
import os
import google.generativeai as genai
from pydantic import BaseModel

router = APIRouter(prefix="/chat")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Get API key from environment
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    print("✅ Gemini API initialized")
else:
    model = None
    print("❌ GEMINI_API_KEY not found")

# Dictionary to store chat histories per user
chat_histories = {}

class ChatRequest(BaseModel):
    message: str
    user_id: int

@router.post("/")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    if not model:
        raise HTTPException(status_code=500, detail="AI Configuration Error")
    
    try:
        user_id = req.user_id
        user_message = req.message

        if user_id not in chat_histories:
            chat_histories[user_id] = []

        chat_session = model.start_chat(history=chat_histories[user_id])
        response = chat_session.send_message(user_message)
        bot_reply = response.text

        chat_histories[user_id] = chat_session.history

        # Save to database
        new_chat = Chat(user_id=user_id, question=user_message, answer=bot_reply)
        db.add(new_chat)
        db.commit()
        print(f"✅ Saved chat to database")

        return {"reply": bot_reply}
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG - API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI Service Error: {str(e)}")

@router.get("/history/{user_id}")
def history(user_id: int, db: Session = Depends(get_db)):
    try:
        rows = db.query(Chat).filter(Chat.user_id == user_id).all()
        return {"history": [{"question": r.question, "answer": r.answer} for r in rows]}
    except Exception as e:
        print(f"Database Error: {e}")
        return {"history": []}
