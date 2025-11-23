from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from producer import KafkaProducerService
from consumer import KafkaConsumerService
import asyncio
import os
from fastapi.responses import FileResponse


app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

producer = KafkaProducerService()
rooms = {}       # {"room_name": {"username": WebSocket}}
consumers = {}   # {"room_name": KafkaConsumerService}

ROOMS = ["general", "random"]
DOCS_DIR = "uploaded_docs"
os.makedirs(DOCS_DIR, exist_ok=True)

# Track connected WebSocket clients by room
# active_connections = {}


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
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "rooms": ROOMS,
        "documents": docs,
        "username": "GuestUser"
    })

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    path = os.path.join(DOCS_DIR, file.filename)
    print("Saving uploaded file to:", path)
    with open(path, "wb") as f:
        f.write(await file.read())
    return file.filename

@app.post("/create_room/{room_name}")
async def create_room(room_name: str):
    if room_name not in ROOMS:
        ROOMS.append(room_name)
    return {"rooms": ROOMS}

@app.get("/download/{filename}")
async def download_file(filename: str):
    return FileResponse(os.path.join(DOCS_DIR, filename))

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


async def start_room_consumer(room: str):
    topic = f"chat-{room}"
    consumer = KafkaConsumerService(topic)
    consumers[room] = consumer

    async def handle_message(message):
        for ws in rooms.get(room, {}).values():
            await ws.send_json(message)

    await consumer.start(handle_message)
