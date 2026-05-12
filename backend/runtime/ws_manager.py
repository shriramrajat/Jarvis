"""
JARVIS OS — WebSocket Manager
Manages all active frontend connections.
Bridges the Event Bus → WebSocket (backend → frontend push).
"""
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from ..event_bus import event_bus, Event, EventType
from ..state import state_manager


@dataclass
class WSClient:
    websocket: WebSocket
    client_id: str
    connected_at: datetime


class WebSocketManager:
    """
    - Tracks all connected WebSocket clients.
    - Broadcasts Event Bus messages to all connected clients.
    - Receives messages from frontend and routes them into the Event Bus.
    """

    def __init__(self):
        self._clients: dict[str, WSClient] = {}
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients[client_id] = WSClient(
                websocket=websocket,
                client_id=client_id,
                connected_at=datetime.utcnow(),
            )
        logger.info(f"[WS] Client connected: {client_id} (total: {self.client_count})")

        # Send current state immediately on connect
        await self._send_to(client_id, {
            "type": "HANDSHAKE",
            "state": state_manager.snapshot.to_dict(),
            "message": "JARVIS OS online",
        })

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            self._clients.pop(client_id, None)
        logger.info(f"[WS] Client disconnected: {client_id} (total: {self.client_count})")

    async def broadcast(self, message: dict) -> None:
        """Send a message to all connected clients."""
        if not self._clients:
            return
        payload = json.dumps(message)
        dead: list[str] = []
        for client_id, client in self._clients.items():
            try:
                await client.websocket.send_text(payload)
            except Exception as e:
                logger.warning(f"[WS] Failed to send to {client_id}: {e}")
                dead.append(client_id)
        for client_id in dead:
            await self.disconnect(client_id)

    async def _send_to(self, client_id: str, message: dict) -> None:
        """Send a message to a specific client."""
        client = self._clients.get(client_id)
        if client:
            try:
                await client.websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"[WS] Send to {client_id} failed: {e}")

    async def handle_client(self, websocket: WebSocket, client_id: str) -> None:
        """Main handler loop for a connected client."""
        await self.connect(websocket, client_id)
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                    await self._route_message(data, client_id)
                except json.JSONDecodeError:
                    logger.warning(f"[WS] Invalid JSON from {client_id}: {raw[:100]}")
        except WebSocketDisconnect:
            await self.disconnect(client_id)
        except Exception as e:
            logger.error(f"[WS] Unexpected error for {client_id}: {e}")
            await self.disconnect(client_id)

    async def _route_message(self, data: dict, client_id: str) -> None:
        """Route an incoming frontend message into the Event Bus."""
        msg_type = data.get("type", "")
        logger.debug(f"[WS] ← {client_id}: {msg_type}")

        event_type_map = {
            "TEXT_INPUT":    EventType.TEXT_INPUT,
            "GUI_INPUT":     EventType.GUI_INPUT,
            "HOTKEY":        EventType.HOTKEY_TRIGGERED,
            "PERMISSION_OK": EventType.PERMISSION_GRANTED,
            "PERMISSION_NO": EventType.PERMISSION_DENIED,
            "SHUTDOWN":      EventType.SYSTEM_SHUTDOWN,
        }

        if msg_type in event_type_map:
            await event_bus.publish(Event(
                type=event_type_map[msg_type],
                data={**data, "client_id": client_id},
                source="websocket",
                priority="HIGH" if msg_type in ("SHUTDOWN", "PERMISSION_OK", "PERMISSION_NO") else "MEDIUM",
            ))
        else:
            logger.warning(f"[WS] Unknown message type: {msg_type}")

    # ── Event Bus → WebSocket bridge ─────────────────────────────────────────

    async def _on_state_changed(self, event: Event) -> None:
        await self.broadcast({"type": "STATE_CHANGED", **event.data})

    async def _on_response_generated(self, event: Event) -> None:
        await self.broadcast({"type": "RESPONSE", **event.data})

    async def _on_permission_required(self, event: Event) -> None:
        await self.broadcast({"type": "PERMISSION_REQUIRED", **event.data})

    async def _on_gui_notification(self, event: Event) -> None:
        await self.broadcast({"type": "NOTIFICATION", **event.data})

    async def _on_context_updated(self, event: Event) -> None:
        await self.broadcast({"type": "CONTEXT_UPDATE", **event.data})

    def register_listeners(self) -> None:
        """Register all Event Bus → WS bridge handlers."""
        event_bus.subscribe(EventType.STATE_CHANGED,        self._on_state_changed)
        event_bus.subscribe(EventType.RESPONSE_GENERATED,   self._on_response_generated)
        event_bus.subscribe(EventType.PERMISSION_REQUIRED,  self._on_permission_required)
        event_bus.subscribe(EventType.GUI_NOTIFICATION,     self._on_gui_notification)
        event_bus.subscribe(EventType.CONTEXT_UPDATED,      self._on_context_updated)
        logger.success("[WS Manager] Event listeners registered")


# ── Singleton ──────────────────────────────────────────────────────────────────

ws_manager = WebSocketManager()
