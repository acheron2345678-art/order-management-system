from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._order_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._merchant_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect_order(self, order_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._order_connections[order_id].add(websocket)

    async def connect_merchant(self, store_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._merchant_connections[store_id].add(websocket)

    async def disconnect_order(self, order_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._order_connections[order_id].discard(websocket)
            if not self._order_connections[order_id]:
                self._order_connections.pop(order_id, None)

    async def disconnect_merchant(self, store_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._merchant_connections[store_id].discard(websocket)
            if not self._merchant_connections[store_id]:
                self._merchant_connections.pop(store_id, None)

    async def _broadcast(self, targets: list[WebSocket], payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            for mapping in (self._order_connections, self._merchant_connections):
                for key in list(mapping.keys()):
                    mapping[key].discard(websocket)
                    if not mapping[key]:
                        mapping.pop(key, None)

    async def broadcast_order(self, order_id: int, payload: dict[str, Any]) -> None:
        await self._broadcast(list(self._order_connections.get(order_id, set())), payload)

    async def broadcast_merchant(self, store_id: int, payload: dict[str, Any]) -> None:
        await self._broadcast(list(self._merchant_connections.get(store_id, set())), payload)


manager = ConnectionManager()
