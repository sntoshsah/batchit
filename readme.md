# Architecture overview (high level)

* **Real-time transport**: WebSockets for real-time messages and WebRTC (with a WebSocket signaling server) for direct P2P audio/video.
* **Presence & routing**: Redis (pub/sub or Redis Streams) for presence, fan-out, and ephemeral message delivery across backend instances.
* **Durable storage**: PostgreSQL for message history and metadata.
* **Background/event processing**: Kafka for analytics, moderation pipelines, and long-term event streaming (optional).
* **Optional queue / retry**: Redis Streams or RabbitMQ for reliable delivery if you need guaranteed once-only processing.
* **Load balancing / scaling**: Nginx / Envoy in front of backend WebSocket servers; Kubernetes for large deployments.
* **Auth / Security**: JWT for auth tokens, TLS everywhere, per-message signature/CSRF protection for WebSocket handshake.

# Which tech for what

* Real-time text/chat: **WebSocket** (FastAPI or Node.js + Socket.IO if you want features).
* P2P voice/video: **WebRTC** for media; **WebSocket** signaling to exchange SDP/ICE.
* Presence & fan-out across server instances: **Redis pub/sub** or **Redis Streams**.
* Message history & queries: **PostgreSQL** (good relational queries, indexing).
* Analytics / audit pipeline: **Kafka** (topic per event type).
* Small-scale mobile-friendly pub/sub: **MQTT** possible but usually WebSocket + Redis is enough.

# Message flow (1:1 text message)

1. Client A sends `send_message` via WebSocket to backend (authenticated).
2. Backend verifies, persists message to PostgreSQL (or writes it asynchronously) and publishes event to Redis channel for the recipient (and to Kafka for analytics).
3. If recipient is connected to any backend instance, that instance receives Redis message and pushes via its WebSocket connection(s) to recipient devices.
4. If recipient is offline, the backend stores delivery state; on reconnect, the client fetches missed messages via REST endpoint or receives sync events on connect.

# Message flow (group chat)

* Option 1: single Redis channel per chat room. Backend publishes to channel; subscribers receive messages.
* Option 2 (large rooms): store member list in Redis, fan-out messages to members either using channel per-user or batching.

# Presence & typing indicators

* On connect, backend stores `user:{id}:ws_instances` and `presence:{id}` in Redis with TTL.
* Typing: ephemeral Redis pub/sub topic `typing:{room_id}` with short TTL.

# Data model (simplified SQL)

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  display_name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  type TEXT NOT NULL, -- 'direct' or 'group'
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE conversation_members (
  conversation_id UUID REFERENCES conversations(id),
  user_id UUID REFERENCES users(id),
  joined_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY(conversation_id, user_id)
);

CREATE TABLE messages (
  id UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id),
  sender_id UUID REFERENCES users(id),
  content JSONB, -- content.type, content.text, content.attachments
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  delivered_at TIMESTAMP WITH TIME ZONE NULL
);
CREATE INDEX ON messages(conversation_id, created_at DESC);
```

# Message JSON format (example)

```json
{
  "type": "text",
  "text": "Hey, are you there?",
  "attachments": [],
  "client_msg_id": "uuid-or-client-id",
  "sent_at": "2025-11-09T09:00:00Z"
}
```

# Delivery guarantees & strategies

* **At-least-once**: simplest — message published to Redis + saved to DB. Deduplication via `client_msg_id`.
* **Exactly-once**: harder; require idempotent writes and careful offsets (use Redis Streams + consumer groups or Kafka).
* **Ordering**: Per-conversation ordering can be achieved by using `created_at` + monotonic sequence per conversation stored in DB.

# Scaling strategy by tier

Small (dev / <1k users):

* Single FastAPI instance (or 2 behind load balancer).
* Redis single instance, PostgreSQL single instance.
* Docker Compose deployment.
* Use WebSockets directly.

Medium (1k–100k active users):

* Multiple FastAPI WebSocket instances behind Nginx; session affinity via cookie or sticky sessions OR use redis for pub/sub across instances.
* Redis Sentinel or managed Redis.
* Postgres with read replicas.
* Use Redis Streams for reliable fan-out.
* Kafka optional for analytics.

Large (100k+ active):

* Kubernetes for autoscaling pods (deployment with Horizontal Pod Autoscaler).
* Redis Cluster.
* Kafka cluster for analytics and event sourcing.
* Sharded PostgreSQL, or scalable stores for older messages (Cassandra / ClickHouse for analytics).
* Use service mesh (Envoy) and observability stack (Prometheus + Grafana + ELK).

# Security & privacy

* TLS for WebSocket endpoints (wss://).
* Authenticate WebSocket handshake (JWT token in `Sec-WebSocket-Protocol` or query param — but prefer header during handshake).
* Rate limiting per user to prevent spam.
* End-to-end encryption optional: use per-conversation key exchange and encrypt payloads on client side (then backend can't read messages).
* Sanitize attachments and run virus/malware checks in background.

# Where Kafka fits

* **Do** use Kafka for analytics, moderation, metrics, long-term event streaming (audit logs, message metrics). Backend publishes user-message events to Kafka topics; separate pipeline services consume for ML/moderation/BI.
* **Don’t** use Kafka as the primary low-latency delivery path for user-facing chat.

# FastAPI WebSocket + Redis pub/sub example

This is a minimal, practical server pattern using `aioredis` + FastAPI. It persists to Postgres asynchronously (example uses `asyncpg` placeholder). It demonstrates sending messages to Redis so other instances can deliver.

```python
# requirements: fastapi uvicorn[standard] aioredis asyncpg python-dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Header
import asyncio
import json
import uuid
import os
import aioredis
# DB save function is illustrative only
# Real app: use SQLAlchemy/asyncpg and proper connection pool

app = FastAPI()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis = None

# in-memory map for local connections: user_id -> set(WebSocket)
LOCAL_CONNECTIONS = {}

async def save_message_to_db(conversation_id, sender_id, message):
    # placeholder: store message in DB (async)
    # return message_id, created_at
    return str(uuid.uuid4()), "now"

async def publish_to_redis(recipient_user_id, payload):
    channel = f"user:{recipient_user_id}:inbox"
    await redis.publish(channel, json.dumps(payload))

@app.on_event("startup")
async def startup_event():
    global redis
    redis = await aioredis.create_redis_pool(REDIS_URL)
    # Start a background listener for incoming Redis messages for this instance if needed:
    # but typically you'll use per-user channels and subscribe only when a user connects.

@app.on_event("shutdown")
async def shutdown_event():
    redis.close()
    await redis.wait_closed()

async def send_to_local(user_id, payload):
    conns = LOCAL_CONNECTIONS.get(user_id, set())
    for ws in list(conns):
        try:
            await ws.send_json(payload)
        except Exception:
            conns.remove(ws)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    # Authenticate token, then get user_id
    await websocket.accept()
    user_id = authenticate_token(token)  # implement this
    LOCAL_CONNECTIONS.setdefault(user_id, set()).add(websocket)

    # Subscribe to Redis personal channel for this connection
    pubsub = await aioredis.create_redis(REDIS_URL)
    ch, = await pubsub.subscribe(f"user:{user_id}:inbox")

    async def reader():
        while await ch.wait_message():
            msg = await ch.get(encoding="utf-8")
            try:
                await websocket.send_text(msg)
            except Exception:
                break

    reader_task = asyncio.create_task(reader())

    try:
        while True:
            data = await websocket.receive_json()
            # data example: {"conversation_id": "...", "to": "recipient_id", "message": {...}}
            conv_id = data["conversation_id"]
            to_user = data["to"]
            message = data["message"]
            # Persist the message (async)
            msg_id, created_at = await save_message_to_db(conv_id, user_id, message)
            payload = {
                "event": "message",
                "message_id": msg_id,
                "conversation_id": conv_id,
                "from": user_id,
                "message": message,
                "created_at": created_at
            }
            # publish to recipient channel (so any instance with recipient delivered it)
            await publish_to_redis(to_user, payload)
            # also publish to analytics Kafka in background (not shown here)
    except WebSocketDisconnect:
        pass
    finally:
        reader_task.cancel()
        LOCAL_CONNECTIONS.get(user_id, set()).discard(websocket)
        await pubsub.unsubscribe(f"user:{user_id}:inbox")
        pubsub.close()
        await pubsub.wait_closed()

# Implement authenticate_token(...) and DB functions appropriately.
```

Notes:

* This example uses Redis pub/sub and personal channels (`user:{id}:inbox`). When multiple backend instances run, whichever instance the recipient is connected to will subscribe to that channel and receive messages posted by any instance.
* For reliability, consider Redis Streams + consumer groups instead of plain pub/sub to avoid message loss when no subscriber is connected.

# WebRTC signaling idea

* Use same WebSocket endpoint for signaling messages: `{"type":"webrtc-offer","to":"userB","sdp":{...}}` then backend relays to recipient via Redis pub/sub. Once ICE/SDP exchange completes, media flows directly between peers (P2P) and backend load is minimal.

# Ops & Observability

* Logs: structured JSON logs (message events should not include plaintext of E2E encrypted messages).
* Metrics: count messages/sec, connected users, latency P50/P95 for delivery.
* Tracing: OpenTelemetry across backend services.
* Monitoring: Prometheus + Grafana; alerts for high Redis memory, Kafka lag, DB CPU.

# Quick recommended stack (practical)

* FastAPI (WebSocket + REST)
* Redis (pub/sub + presence + optionally Redis Streams)
* PostgreSQL (history)
* Kafka (analytics/moderation)
* Nginx/Envoy + Kubernetes
* TLS termination at ingress (Let’s Encrypt / managed certs)