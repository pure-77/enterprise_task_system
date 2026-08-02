"""WebSocket 多通道连接管理 — 支持 IM + 通知 + 任务状态"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
import threading
import pytz
from datetime import datetime
from app.db.redis_client import get_redis

BEIJING_TZ = pytz.timezone('Asia/Shanghai')


def get_beijing_time_str():
    return datetime.now(BEIJING_TZ).replace(tzinfo=None).isoformat()


router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器 — 支持多通道订阅"""

    def __init__(self):
        # user_id -> [websocket]
        self.connections: dict[int, list[WebSocket]] = {}
        # user_id -> set of subscribed channels
        self.subscriptions: dict[int, set] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
            self.subscriptions[user_id] = set()
        self.connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.connections:
            if websocket in self.connections[user_id]:
                self.connections[user_id].remove(websocket)
            if not self.connections[user_id]:
                del self.connections[user_id]
                if user_id in self.subscriptions:
                    del self.subscriptions[user_id]

    def subscribe(self, user_id: int, channels: list[str]):
        if user_id in self.subscriptions:
            for ch in channels:
                self.subscriptions[user_id].add(ch)

    def unsubscribe(self, user_id: int, channels: list[str]):
        if user_id in self.subscriptions:
            for ch in channels:
                self.subscriptions[user_id].discard(ch)

    async def send_to_user(self, user_id: int, data: dict):
        """发送消息给指定用户的所有连接"""
        if user_id in self.connections:
            dead = []
            for ws in self.connections[user_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws, user_id)

    async def send_to_channel(self, channel: str, data: dict, user_ids: list[int] = None):
        """发送消息给订阅了指定频道的所有用户"""
        for uid, subs in self.subscriptions.items():
            if user_ids and uid not in user_ids:
                continue
            if channel in subs:
                await self.send_to_user(uid, data)


manager = ConnectionManager()


# ==================== Redis Pub/Sub 辅助 ====================

def publish_im_message(conversation_id: int, message_data: dict):
    """发布 IM 消息到 Redis — Redis 不可用时静默跳过"""
    try:
        get_redis().publish(
            f"im:conversation:{conversation_id}",
            json.dumps({
                "channel": "im",
                "type": "new_message",
                "data": message_data
            })
        )
    except Exception:
        pass


def publish_notification(user_id: int, notification_data: dict):
    """发布通知到 Redis"""
    try:
        get_redis().publish(
            f"notification:user:{user_id}",
            json.dumps({
                "channel": "notification",
                "type": "new_notification",
                "data": notification_data
            })
        )
    except Exception:
        pass


def publish_task_event(user_id: int, task_data: dict):
    """发布任务事件到 Redis（保留兼容）"""
    try:
        get_redis().publish(
            "task_status_updates",
            json.dumps({
                "channel": "task",
                "type": "task_status_update",
                "user_id": user_id,
                "data": task_data,
                "timestamp": get_beijing_time_str()
            })
        )
    except Exception:
        pass


# ==================== Redis 订阅线程 ====================

_loop = None
_shutdown_event = threading.Event()

CHANNELS = [
    "task_status_updates",
    "workspace_events",
    "im:*",  # 模式订阅
    "notification:*",
]


def redis_subscriber():
    """Redis 订阅者 — 多频道监听"""
    redis_client = get_redis()
    max_retries = 3

    for attempt in range(max_retries):
        if _shutdown_event.is_set():
            break
        try:
            pubsub = redis_client.pubsub()
            # 订阅精确频道
            pubsub.subscribe("task_status_updates", "workspace_events")
            # 订阅模式频道
            pubsub.psubscribe("im:conversation:*", "notification:user:*")

            print("Redis subscriber started, listening on multiple channels...")

            for message in pubsub.listen():
                if _shutdown_event.is_set():
                    break
                if message['type'] in ('message', 'pmessage'):
                    try:
                        data = json.loads(message['data'])
                        channel_name = data.get("channel", "task")
                        user_id = data.get("user_id")

                        if _loop:
                            if user_id:
                                asyncio.run_coroutine_threadsafe(
                                    manager.send_to_user(user_id, data), _loop
                                )
                            else:
                                asyncio.run_coroutine_threadsafe(
                                    manager.send_to_channel(channel_name, data), _loop
                                )
                    except (json.JSONDecodeError, Exception) as e:
                        print(f"Redis message handling error: {e}")

            pubsub.close()
        except Exception as e:
            print(f"Redis subscriber error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1 and not _shutdown_event.is_set():
                _shutdown_event.wait(5)
            else:
                print("Redis subscriber failed. WebSocket features may be unavailable.")


# ==================== WebSocket 端点 ====================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """多通道 WebSocket 端点 — 支持 subscribe/unsubscribe"""
    try:
        from app.core.security import decode_token
        payload = decode_token(token)
        if not payload:
            await websocket.close(code=1008, reason="Invalid token")
            return

        user_id = payload.get('user_id')
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return

        await manager.connect(websocket, user_id)
        await manager.send_to_user(user_id, {
            "type": "connected",
            "message": "WebSocket connection established",
            "channel": "system"
        })

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                action = msg.get("action")
                channels = msg.get("channels", [])

                if action == "subscribe" and channels:
                    manager.subscribe(user_id, channels)
                    await manager.send_to_user(user_id, {
                        "type": "subscribed",
                        "channels": list(manager.subscriptions.get(user_id, set())),
                        "channel": "system"
                    })
                elif action == "unsubscribe" and channels:
                    manager.unsubscribe(user_id, channels)
                elif action == "ping":
                    await websocket.send_json({"type": "pong", "channel": "system"})
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if 'user_id' in locals():
            manager.disconnect(websocket, user_id)


def start_redis_subscriber():
    global _loop
    try:
        _loop = asyncio.get_running_loop()
    except RuntimeError:
        _loop = asyncio.get_event_loop()
    _shutdown_event.clear()
    thread = threading.Thread(target=redis_subscriber, daemon=True)
    thread.start()


def stop_redis_subscriber():
    _shutdown_event.set()
