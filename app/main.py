from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import asyncio, os, json
from kafka_manager import KafkaManager

app = FastAPI()
templates = Jinja2Templates(directory="templates")

kafka = KafkaManager()
ROOMS = ["general", "random"]
DOCS_DIR = "uploaded_docs"
os.makedirs(DOCS_DIR, exist_ok=True)

# Track connected WebSocket clients by room
active_connections = {}

@app.on_event("startup")
async def startup_event():
    await kafka.start_producer()

@app.on_event("shutdown")
async def shutdown_event():
    await kafka.stop_producer()

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
async def upload_file(file: UploadFile):
    path = os.path.join(DOCS_DIR, file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"success": True}

@app.post("/create_room/{room_name}")
async def create_room(room_name: str):
    if room_name not in ROOMS:
        ROOMS.append(room_name)
    return {"rooms": ROOMS}

@app.get("/download/{filename}")
async def download_file(filename: str):
    return FileResponse(os.path.join(DOCS_DIR, filename))

# 🟢 WebSocket Endpoint
@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(websocket: WebSocket, room: str, username: str):
    await websocket.accept()

    if room not in active_connections:
        active_connections[room] = []
    active_connections[room].append(websocket)

    consumer = await kafka.create_consumer(topic=room, group_id=f"group_{room}")

    try:
        # Consume messages concurrently
        consumer_task = asyncio.create_task(kafka_consumer_loop(consumer, room, websocket))
        
        # Receive messages from client
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            payload = {"from": username, "text": message["text"]}
            await kafka.produce_message(topic=room, message=payload)

    except WebSocketDisconnect:
        print(f"❌ {username} disconnected from {room}")
        active_connections[room].remove(websocket)
        await consumer.stop()
        consumer_task.cancel()

async def kafka_consumer_loop(consumer, room, websocket):
    """Continuously listen to Kafka topic and broadcast messages to room."""
    try:
        async for msg in consumer:
            message = msg.value
            # Broadcast to all connected clients in this room
            websockets = active_connections.get(room, [])
            for ws in websockets:
                if ws.application_state.name == "CONNECTED":
                    await ws.send_json(message)
    except asyncio.CancelledError:
        await consumer.stop()
