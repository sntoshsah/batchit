import bcrypt
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from producer import KafkaProducerService
from consumer import KafkaConsumerService
import asyncio
import os
from fastapi.responses import FileResponse
from models import User, Group, GroupUser, Message, Document, Topic
from database import SessionLocal, engine, Base
from schemas import UserCreate, GroupCreate, TopicCreate, MessageCreate, DocumentCreate, DocumentUpdate
from sqlalchemy.orm import Session
from ws_manager import manager

Base.metadata.create_all(bind=engine)



app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

producer = KafkaProducerService()
rooms = {}       # {"room_name": {"username": WebSocket}}
consumers = {}   # {"room_name": KafkaConsumerService}

ROOMS = ["general", "random"]
DOCS_DIR = "uploaded_docs"
os.makedirs(DOCS_DIR, exist_ok=True)


@app.on_event("startup")
async def startup_event():
    await producer.start()


@app.on_event("shutdown")
async def shutdown_event():
    await producer.stop()
    for consumer in consumers.values():
        await consumer.consumer.stop()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    docs = os.listdir(DOCS_DIR)
    username = request.cookies.get("username", "GuestUser")  # Temp user if no cookie

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "rooms": ROOMS,
        "documents": docs,
        "username": username,
        "login_url": "/login"  # Provide login page URL
    })

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    path = os.path.join(DOCS_DIR, file.filename)
    print("Saving uploaded file to:", path)
    with open(path, "wb") as f:
        f.write(await file.read())
# After upload, list files again and render the template
    docs = os.listdir(DOCS_DIR)
    username = request.cookies.get("username", "GuestUser")
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "rooms": ROOMS,
        "documents": docs,
        "username": username,
        "login_url": "/login"
    })

@app.post("/create_room/{room_name}")
async def create_room(room_name: str):
    if room_name not in ROOMS:
        ROOMS.append(room_name)
    return {"rooms": ROOMS}

@app.get("/download/{filename}")
async def download_file(filename: str):
    return FileResponse(os.path.join(DOCS_DIR, filename))

@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    path = os.path.join(DOCS_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return {"status": "deleted"}
    return {"status": "file not found"}

@app.post("/login")
async def login(request: Request):
    # Implement login logic here
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    db: Session = next(get_db())
    user = db.query(User).filter(User.username == username).first()
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return {"error": "Invalid credentials"}
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="username", value=username)
    return response


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("partials/_login.html", {"request": request})

@app.get("/logout", response_class=HTMLResponse)
async def logout_page(request: Request):
    return templates.TemplateResponse("partials/_logout.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("partials/_register.html", {"request": request})

@app.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    # Implement registration logic here
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    confirm_password = form.get("confirm_password")
    if password != confirm_password:
        return {"error": "Passwords do not match"}
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user = User(username=username, password_hash=str(password_hash.decode('utf-8')))
    db.add(user)
    db.commit()
    db.refresh(user)
    return HTMLResponse("Registration successful. You can now log in.")


# # ---- CRUD ----

# @app.post("/users/")
# def create_user(user: UserCreate, db: Session = Depends(get_db)):
#     db_user = User(username=user.username)
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user

@app.post("/groups/")
def create_group(group: GroupCreate, db: Session = Depends(get_db)):
    db_group = Group(name=group.name)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

@app.post("/groups/{group_id}/join/{user_id}")
def join_group(group_id: int, user_id: int, db: Session = Depends(get_db)):
    gu = GroupUser(group_id=group_id, user_id=user_id)
    db.add(gu)
    db.commit()
    return {"message": "User joined group"}

@app.post("/topics/")
def create_topic(topic: TopicCreate, db: Session = Depends(get_db)):
    t = Topic(name=topic.name, group_id=topic.group_id)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

@app.post("/messages/")
def post_message(msg: MessageCreate, db: Session = Depends(get_db)):
    message = Message(**msg.dict())
    db.add(message)
    db.commit()
    db.refresh(message)
    # Notify via WebSocket
    import asyncio
    asyncio.create_task(manager.broadcast(msg.topic_id, f"New message from user {msg.user_id}: {msg.content}"))
    return message

@app.post("/documents/")
def post_document(doc: DocumentCreate, db: Session = Depends(get_db)):
    document = Document(**doc.dict())
    db.add(document)
    db.commit()
    db.refresh(document)
    import asyncio
    asyncio.create_task(manager.broadcast(doc.topic_id, f"New document '{doc.title}' by user {doc.user_id}"))
    return document

@app.put("/documents/{doc_id}")
def update_document(doc_id: int, doc_update: DocumentUpdate, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return {"error": "Document not found"}
    doc.title = doc_update.title
    doc.content = doc_update.content
    db.commit()
    db.refresh(doc)
    import asyncio
    asyncio.create_task(manager.broadcast(doc.topic_id, f"Document '{doc.title}' updated"))
    return doc

@app.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return {"error": "Document not found"}
    db.delete(doc)
    db.commit()
    import asyncio
    asyncio.create_task(manager.broadcast(doc.topic_id, f"Document '{doc.title}' deleted"))
    return {"message": "Document deleted"}



@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await websocket.accept()
    if room not in rooms:
        rooms[room] = {}
        asyncio.create_task(start_room_consumer(room))
    rooms[room][username] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            message = {"room": room, "from": username, "text": data["text"]}
            await producer.send_message(f"chat-{room}", message)
    except WebSocketDisconnect:
        del rooms[room][username]
        if not rooms[room]:
            del rooms[room]



# Track connected WebSocket clients by room
active_connections = {}

async def start_room_consumer(room: str):
    topic = f"chat-{room}"
    consumer = KafkaConsumerService(topic)
    consumers[room] = consumer

    async def handle_message(message):
        for ws in rooms.get(room, {}).values():
            await ws.send_json(message)

    await consumer.start(handle_message)
