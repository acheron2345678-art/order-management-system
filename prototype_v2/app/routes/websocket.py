from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..realtime.manager import manager

router = APIRouter(tags=["Realtime"])


@router.websocket("/ws/orders/{order_id}")
async def order_socket(websocket: WebSocket, order_id: int):
    await manager.connect_order(order_id, websocket)
    try:
        await websocket.send_json({"type": "CONNECTED", "order_id": order_id})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_order(order_id, websocket)


@router.websocket("/ws/merchants/{store_id}")
async def merchant_socket(websocket: WebSocket, store_id: int):
    await manager.connect_merchant(store_id, websocket)
    try:
        await websocket.send_json({"type": "CONNECTED", "store_id": store_id})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_merchant(store_id, websocket)
