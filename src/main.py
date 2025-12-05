from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from producer import KafkaProducerService
from consumer import KafkaConsumerService
import asyncio
import os
from database import engine, Base, get_db
from sqlalchemy.orm import Session
from schemas.message import MessageCreate
from ws_manager import manager
from routes.home import home_router
from routes.users import users_router
from routes.knowledge import knowledge_router
from routes.room import room_router
from models import Room
from starlette.middleware.sessions import SessionMiddleware


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(home_router)
app.include_router(users_router)
app.include_router(knowledge_router)
app.include_router(room_router)



app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key="abcd1234efgh5678")  # Replace with a secure key in production


templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

producer = KafkaProducerService()
rooms = {}       # {"room_name": {"username": WebSocket}}
consumers = {}   # {"room_name": KafkaConsumerService}


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


@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str, db: Session = Depends(get_db)):
    room_obj = db.query(Room).filter(Room.name == room).first()
    if not room_obj:
        await websocket.close(code=1000)
        return
    
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

@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str, db: Session = Depends(get_db)):
    room_obj = db.query(Room).filter(Room.name == room).first()
    if not room_obj:
        await websocket.close(code=1000)
        return
    
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



async def start_room_consumer(room: str):
    topic = f"chat-{room}"
    consumer = KafkaConsumerService(topic)
    consumers[room] = consumer

    async def handle_message(message):
        for ws in rooms.get(room, {}).values():
            await ws.send_json(message)

    await consumer.start(handle_message)
