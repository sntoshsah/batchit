from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
import os
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from models import Room


templates = Jinja2Templates(directory="templates")

home_router = APIRouter()

DOCS_DIR = "uploaded_docs"
os.makedirs(DOCS_DIR, exist_ok=True)


@home_router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    docs = os.listdir(DOCS_DIR)
    username = request.cookies.get("username", "GuestUser")  # Temp user if no cookie
    rooms = db.query(Room).all()
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "rooms": rooms,
        "documents": docs,
        "username": username,
        "login_url": "/login"  # Provide login page URL
    })