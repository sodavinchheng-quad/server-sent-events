from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
from constants import STORES
from entities import Client
import json
import asyncio

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.root_path = "/api"

store_clients: Dict[int, List[Client]] = {}


# Get stores
@app.get("/stores")
def get_stores():
    return [store.to_dict() for store in STORES.values()]


# Get tables for a specific store
@app.get("/stores/{store_id}/tables")
def get_tables(store_id: int):
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail="Store not found")

    return [table.to_dict() for table in STORES[store_id].tables.values()]


@app.get("/check_status")
def check_status():
    store_clients_count = {
        store_id: len(clients) for store_id, clients in store_clients.items()
    }
    total_clients = sum(store_clients_count.values())
    return {
        "total_clients": total_clients,
        "store_clients_count": store_clients_count,
    }


# Update table status for a specific table in a specific store
@app.post("/stores/{store_id}/tables/{table_id}/update")
async def update_table_status(store_id: int, table_id: int, request: Request):
    data: Dict = await request.json()
    status = data.get("status")

    if store_id not in STORES:
        raise HTTPException(status_code=404, detail="Store not found")

    store = STORES[store_id]
    if table_id not in store.tables:
        raise HTTPException(status_code=404, detail="Table not found")

    table = store.tables[table_id]
    try:
        table.update_status(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    return {"message": "Status updated"}


# Send a message to all clients connected to a specific store via SSE
@app.post("/stores/{store_id}/push_message")
async def push_message(store_id: int, request: Request):
    data: Dict = await request.json()
    message = data.get("message")

    if store_id not in STORES:
        raise HTTPException(status_code=404, detail="Store not found")

    clients = store_clients.get(store_id)

    for client in clients:
        await client.send(json.dumps({"message": message}))

    return {"message": f"Message pushed to {len(clients)} clients"}


# SSE for real-time updates (listening to store table status changes)
@app.get("/events/{store_id}")
async def sse_events(store_id: int):
    if store_id not in STORES:
        raise HTTPException(status_code=404, detail="Store not found")

    client = Client(store=STORES[store_id])
    store_clients.setdefault(store_id, []).append(client)

    task = asyncio.create_task(periodic_status_update(client, store_id))
    client.set_task(task)

    def on_cancel():
        store_clients[store_id].remove(client)
        client.cancel()

    return StreamingResponse(
        client.listen(on_cancel),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
        media_type="text/event-stream",
    )


# Periodic status update task
async def periodic_status_update(client: Client, store_id: int):
    try:
        while True:
            new_status = [
                table.to_dict() for table in STORES[store_id].tables.values()
            ]
            await client.send(json.dumps(new_status))
            await asyncio.sleep(10)  # Send updates every 10 seconds
    except asyncio.CancelledError:
        pass


def cancel_tasks():
    for clients in store_clients.values():
        for client in clients:
            client.cancel()


app.add_event_handler("shutdown", cancel_tasks)
