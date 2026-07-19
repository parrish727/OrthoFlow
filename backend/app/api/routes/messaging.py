"""OrthoFlow — DA Real-Time Messaging routes + WebSocket."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, decode_token
from app.core.database import get_db
from app.models.messaging import ChatRoom, ChatRoomMember, ChatMessage

router = APIRouter(prefix="/api/v1/chat")


# ── Schemas ───────────────────────────────────────────────────────────────────


class CreateRoomRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    room_type: Literal["general", "direct", "group"] = "general"
    member_ids: list[str] = Field(..., min_length=1)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: Literal["text", "emoji", "system"] = "text"


class RoomResponse(BaseModel):
    id: str
    name: str
    room_type: str
    is_archived: bool
    created_at: str
    member_count: int


class MessageResponse(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: str
    is_edited: bool
    created_at: str


# ── Connection Manager ────────────────────────────────────────────────────────


class ConnectionManager:
    """In-memory WebSocket connection manager keyed by room_id."""

    def __init__(self) -> None:
        self._connections: dict[str, dict[WebSocket, dict]] = {}

    async def connect(self, room_id: str, websocket: WebSocket, user_info: dict) -> None:
        await websocket.accept()
        if room_id not in self._connections:
            self._connections[room_id] = {}
        self._connections[room_id][websocket] = user_info

    def disconnect(self, room_id: str, websocket: WebSocket) -> None:
        if room_id in self._connections:
            self._connections[room_id].pop(websocket, None)
            if not self._connections[room_id]:
                del self._connections[room_id]

    async def broadcast(self, room_id: str, message: dict, exclude: WebSocket | None = None) -> None:
        if room_id not in self._connections:
            return
        dead: list[WebSocket] = []
        for ws in self._connections[room_id]:
            if ws is exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[room_id].pop(ws, None)


manager = ConnectionManager()


# ── REST Endpoints ────────────────────────────────────────────────────────────


@router.get("/rooms")
async def list_rooms(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RoomResponse]:
    """List chat rooms the current user is a member of."""
    result = await db.execute(
        select(ChatRoom)
        .join(ChatRoomMember, ChatRoomMember.room_id == ChatRoom.id)
        .where(
            and_(
                ChatRoomMember.user_id == uuid.UUID(user["user_id"]),
                ChatRoom.practice_id == uuid.UUID(user["practice_id"]),
                ChatRoom.is_archived == False,  # noqa: E712
            )
        )
        .order_by(ChatRoom.created_at.desc())
    )
    rooms = result.scalars().all()

    responses: list[RoomResponse] = []
    for room in rooms:
        member_count_result = await db.execute(
            select(ChatRoomMember).where(ChatRoomMember.room_id == room.id)
        )
        member_count = len(member_count_result.scalars().all())
        responses.append(
            RoomResponse(
                id=str(room.id),
                name=room.name,
                room_type=room.room_type,
                is_archived=room.is_archived,
                created_at=room.created_at.isoformat(),
                member_count=member_count,
            )
        )
    return responses


@router.post("/rooms", status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: CreateRoomRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoomResponse:
    """Create a new chat room and add members."""
    practice_id = uuid.UUID(user["practice_id"])
    creator_id = uuid.UUID(user["user_id"])

    room = ChatRoom(
        practice_id=practice_id,
        name=payload.name,
        room_type=payload.room_type,
        created_by=creator_id,
    )
    db.add(room)
    await db.flush()

    # Add creator as member
    all_member_ids = set(payload.member_ids)
    all_member_ids.add(user["user_id"])

    for mid in all_member_ids:
        member = ChatRoomMember(room_id=room.id, user_id=uuid.UUID(mid))
        db.add(member)

    await db.commit()
    await db.refresh(room)

    return RoomResponse(
        id=str(room.id),
        name=room.name,
        room_type=room.room_type,
        is_archived=room.is_archived,
        created_at=room.created_at.isoformat(),
        member_count=len(all_member_ids),
    )


@router.get("/rooms/{room_id}/messages")
async def get_messages(
    room_id: str,
    limit: int = Query(50, ge=1, le=200),
    before: str | None = Query(None, description="ISO timestamp for cursor pagination"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    """Get messages in a room with cursor-based pagination."""
    room_uuid = uuid.UUID(room_id)

    # Verify membership
    membership = await db.execute(
        select(ChatRoomMember).where(
            and_(
                ChatRoomMember.room_id == room_uuid,
                ChatRoomMember.user_id == uuid.UUID(user["user_id"]),
            )
        )
    )
    if not membership.scalars().first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this room")

    query = select(ChatMessage).where(ChatMessage.room_id == room_uuid)

    if before:
        cursor_ts = datetime.fromisoformat(before)
        query = query.where(ChatMessage.created_at < cursor_ts)

    query = query.order_by(ChatMessage.created_at.desc()).limit(limit)
    result = await db.execute(query)
    messages = result.scalars().all()

    # Fetch sender names (simple approach — works for small room sizes)
    from app.models.models import User as UserModel

    sender_ids = {m.sender_id for m in messages}
    sender_names: dict[uuid.UUID, str] = {}
    if sender_ids:
        users_result = await db.execute(
            select(UserModel).where(UserModel.id.in_(sender_ids))
        )
        for u in users_result.scalars().all():
            sender_names[u.id] = u.full_name if hasattr(u, "full_name") else u.email

    return [
        MessageResponse(
            id=str(m.id),
            sender_id=str(m.sender_id),
            sender_name=sender_names.get(m.sender_id, "Unknown"),
            content=m.content,
            message_type=m.message_type,
            is_edited=m.is_edited,
            created_at=m.created_at.isoformat(),
        )
        for m in reversed(messages)  # Return chronological order
    ]


@router.post("/rooms/{room_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: str,
    payload: SendMessageRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Send a message to a chat room (REST fallback)."""
    room_uuid = uuid.UUID(room_id)
    sender_uuid = uuid.UUID(user["user_id"])

    # Verify membership
    membership = await db.execute(
        select(ChatRoomMember).where(
            and_(
                ChatRoomMember.room_id == room_uuid,
                ChatRoomMember.user_id == sender_uuid,
            )
        )
    )
    if not membership.scalars().first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this room")

    msg = ChatMessage(
        room_id=room_uuid,
        sender_id=sender_uuid,
        content=payload.content,
        message_type=payload.message_type,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Get sender name
    from app.models.models import User as UserModel

    sender_result = await db.execute(select(UserModel).where(UserModel.id == sender_uuid))
    sender = sender_result.scalars().first()
    sender_name = sender.full_name if sender and hasattr(sender, "full_name") else (sender.email if sender else "Unknown")

    response = MessageResponse(
        id=str(msg.id),
        sender_id=str(msg.sender_id),
        sender_name=sender_name,
        content=msg.content,
        message_type=msg.message_type,
        is_edited=msg.is_edited,
        created_at=msg.created_at.isoformat(),
    )

    # Broadcast to connected WebSocket clients
    await manager.broadcast(
        room_id,
        {"type": "message", "data": response.model_dump()},
    )

    return response


# ── WebSocket Endpoint ────────────────────────────────────────────────────────


@router.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str, token: str = Query(...)):
    """WebSocket endpoint for real-time messaging in a chat room."""
    # Validate JWT
    try:
        payload = decode_token(token)
    except HTTPException:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload["sub"]
    practice_id = payload["practice_id"]

    # Verify room membership
    db: AsyncSession
    async for db in get_db():
        membership = await db.execute(
            select(ChatRoomMember).where(
                and_(
                    ChatRoomMember.room_id == uuid.UUID(room_id),
                    ChatRoomMember.user_id == uuid.UUID(user_id),
                )
            )
        )
        member = membership.scalars().first()
        if not member:
            await websocket.close(code=4003, reason="Not a member of this room")
            return

        # Get user name for broadcasts
        from app.models.models import User as UserModel

        user_result = await db.execute(select(UserModel).where(UserModel.id == uuid.UUID(user_id)))
        user_record = user_result.scalars().first()
        user_name = user_record.full_name if user_record and hasattr(user_record, "full_name") else (user_record.email if user_record else "Unknown")
        break

    user_info = {"user_id": user_id, "user_name": user_name, "practice_id": practice_id}
    await manager.connect(room_id, websocket, user_info)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                # Save to database
                content = data.get("data", {}).get("content", "").strip()
                message_type = data.get("data", {}).get("message_type", "text")

                if not content:
                    continue
                if message_type not in ("text", "emoji", "system"):
                    message_type = "text"

                async for db in get_db():
                    msg = ChatMessage(
                        room_id=uuid.UUID(room_id),
                        sender_id=uuid.UUID(user_id),
                        content=content,
                        message_type=message_type,
                    )
                    db.add(msg)
                    await db.commit()
                    await db.refresh(msg)
                    break

                broadcast_data = {
                    "type": "message",
                    "data": {
                        "id": str(msg.id),
                        "sender_id": user_id,
                        "sender_name": user_name,
                        "content": msg.content,
                        "message_type": msg.message_type,
                        "created_at": msg.created_at.isoformat(),
                    },
                }
                await manager.broadcast(room_id, broadcast_data)

            elif msg_type == "typing":
                # Broadcast typing indicator to others
                typing_data = {
                    "type": "typing",
                    "data": {
                        "user_id": user_id,
                        "user_name": user_name,
                    },
                }
                await manager.broadcast(room_id, typing_data, exclude=websocket)

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
    except Exception:
        manager.disconnect(room_id, websocket)
