import bcrypt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import os
from fastapi.templating import Jinja2Templates
from requests import Session

from database import get_db
from models import User

templates = Jinja2Templates(directory="templates")

users_router = APIRouter()


@users_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("partials/_login.html", {"request": request})


@users_router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    # db: Session = next(get_db())
    user = db.query(User).filter(User.username == username).first()
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.hashed_password.encode('utf-8')):
        return {"error": "Invalid credentials"}
    
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="username", value=username)
    request.session["user_id"] = user.id
    return response

@users_router.get("/logout", response_class=HTMLResponse)
async def logout_page(request: Request):
    return templates.TemplateResponse("partials/_logout.html", {"request": request})

@users_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("partials/_register.html", {"request": request})

@users_router.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    # Implement registration logic here
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    email = form.get("email")
    confirm_password = form.get("confirm_password")
    if password != confirm_password:
        return {"error": "Passwords do not match"}
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user = User(username=username, email=email, hashed_password=str(password_hash.decode('utf-8')))
    db.add(user)
    db.commit()
    db.refresh(user)
    return RedirectResponse(url="/login", status_code=302)

