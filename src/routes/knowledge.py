from fastapi import APIRouter, Depends, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from database import get_db
import os
from fastapi.templating import Jinja2Templates
from models import Knowledge,Room

templates = Jinja2Templates(directory="templates")

DOCS_DIR = "uploaded_docs"
os.makedirs(DOCS_DIR, exist_ok=True)

knowledge_router = APIRouter()


@knowledge_router.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...), db:Session = Depends(get_db)):
    path = os.path.join(DOCS_DIR, file.filename)
    print("Saving uploaded file to:", path)
    with open(path, "wb") as f:
        f.write(await file.read())
# After upload, list files again and render the template
    user_id = request.cookies.get("user_id")
    room_id = request.cookies.get("room_id")
    new_doc = Knowledge(filename=file.filename, filesize_kb=os.path.getsize(path)//1024, filepath=path, room_id=int(room_id) if room_id and room_id.isdigit() else None, user_id=int(user_id) if user_id and user_id.isdigit() else None)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

@knowledge_router.get("/knowledge", response_class=HTMLResponse)
async def knowledge_page(request: Request, db: Session = Depends(get_db)):
    docs = os.listdir(DOCS_DIR)
    username = request.cookies.get("username", "GuestUser")
    rooms = db.query(Room).all()
    room_id = request.cookies.get("room_id")
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "rooms": rooms,
        "documents": docs,
        "username": username,
        "login_url": "/login"
    })



@knowledge_router.get("/download/{filename}")
async def download_file(filename: str):
    return FileResponse(os.path.join(DOCS_DIR, filename))

@knowledge_router.delete("/delete/{filename}")
async def delete_file(filename: str):
    path = os.path.join(DOCS_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return {"status": "deleted"}
    return {"status": "file not found"}
