from fastapi import WebSocket


# ---- WebSocket Connection Manager ----
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}  # topic_id -> websockets

    async def connect(self, websocket: WebSocket, topic_id: int):
        await websocket.accept()
        if topic_id not in self.active_connections:
            self.active_connections[topic_id] = []
        self.active_connections[topic_id].append(websocket)

    def disconnect(self, websocket: WebSocket, topic_id: int):
        if topic_id in self.active_connections:
            self.active_connections[topic_id].remove(websocket)

    async def broadcast(self, topic_id: int, message: dict):
        if topic_id in self.active_connections:
            for connection in self.active_connections[topic_id]:
                await connection.send_json(message)

manager = ConnectionManager()