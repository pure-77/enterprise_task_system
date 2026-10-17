"""WebSocket 多通道连接管理 — 支持 IM + 通知 + 任务状态"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
import threading
import pytz
import redis
from datetime import datetime
from app.db.redis_client import get_redis
from app.core.config import settings

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
        else:
            print(f"[WS] User {user_id} not connected, message dropped")

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
    """发布 IM 消息到 Redis"""
    try:
        result = get_redis().publish(
            f"im:conversation:{conversation_id}",
            json.dumps({
                "channel": "im",
                "type": "new_message",
                "data": message_data
            })
        )
        print(f"[Redis] Published IM message to conv {conversation_id}, subscribers: {result}")
    except Exception as e:
        print(f"[Redis] Failed to publish IM message: {e}")


def publish_notification(user_id: int, notification_data: dict):
    """发布通知到 Redis"""
    try:
        get_redis().publish(
            f"notification:user:{user_id}",
            json.dumps({
                "channel": "notification",
                "type": "new_notification",
                # 顶层必须带 user_id：订阅线程按 user_id 走 send_to_user 定向推送；
                # 缺失时会掉进 send_to_channel("notification") 分支，而前端从不订阅该 channel → 推送被静默丢弃
                "user_id": user_id,
                "data": notification_data
            })
        )
    except Exception:
        pass


def publish_read_status(conversation_id: int, reader_id: int, message_ids: list[int], member_ids: list[int]):
    """发布已读状态到 Redis — 通知会话中其他成员"""
    try:
        get_redis().publish(
            f"im:conversation:{conversation_id}",
            json.dumps({
                "channel": "im",
                "type": "read_status",
                "data": {
                    "conversation_id": conversation_id,
                    "reader_id": reader_id,
                    "message_ids": message_ids,
                },
                "user_ids": [uid for uid in member_ids if uid != reader_id]
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
    """Redis 订阅者 — 多频道监听，带自动重连"""
    while not _shutdown_event.is_set():
        try:
            # 每次重连使用新的 Redis 连接（socket_timeout=None 让 listen 永久阻塞）
            redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=None,
                socket_connect_timeout=5
            )
            redis_client.ping()
            print(f"[Redis Subscriber] Connected to {settings.REDIS_URL}")

            pubsub = redis_client.pubsub()
            pubsub.subscribe("task_status_updates", "workspace_events")
            pubsub.psubscribe("im:conversation:*", "notification:user:*")

            print("[Redis Subscriber] Listening on channels...")

            # 使用 timeout 轮询，定期检查关闭信号和连接健康
            while not _shutdown_event.is_set():
                message = pubsub.get_message(timeout=1.0)
                if message is None:
                    continue
                if _shutdown_event.is_set():
                    break
                if message['type'] in ('message', 'pmessage'):
                    try:
                        data = json.loads(message['data'])
                        channel_name = data.get("channel", "task")
                        user_id = data.get("user_id")
                        msg_type = data.get("type", "unknown")
                        print(f"[Redis] Received: channel={channel_name}, type={msg_type}")

                        if _loop:
                            user_ids = data.get("user_ids")
                            if user_ids:
                                # 多用户推送（如已读状态）
                                for uid in user_ids:
                                    asyncio.run_coroutine_threadsafe(
                                        manager.send_to_user(uid, data), _loop
                                    )
                            elif user_id:
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
            print(f"[Redis Subscriber] Error: {e}")
            if not _shutdown_event.is_set():
                print("[Redis Subscriber] Reconnecting in 5 seconds...")
                _shutdown_event.wait(5)


# ==================== WebSocket 端点 ====================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """多通道 WebSocket 端点 — 支持 subscribe/unsubscribe"""
    user_id = None
    try:
        from app.core.security import decode_token

        # 从 query 参数提取 token（兼容中间件处理后的请求）
        if not token:
            token = websocket.query_params.get("token")

        if not token:
            print("WebSocket: missing token parameter")
            await websocket.close(code=1008, reason="Missing token")
            return

        payload = decode_token(token)
        if not payload:
            print(f"WebSocket: invalid token")
            await websocket.close(code=1008, reason="Invalid token")
            return

        user_id = payload.get('user_id')
        if not user_id:
            print(f"WebSocket: token has no user_id")
            await websocket.close(code=1008, reason="Invalid token")
            return

        print(f"WebSocket: user {user_id} connecting")

        await manager.connect(websocket, user_id)
        print(f"WebSocket: user {user_id} connected successfully")
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
