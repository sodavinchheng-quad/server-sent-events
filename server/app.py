from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
from entities import Client, Store
from gcs import get_store_table_data_from_gcs, get_stores_from_gcs
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

stores = get_stores_from_gcs()
STORES: Dict[int, Store] = {
    store["id"]: Store(store["id"], store["name"]) for store in stores
}


# Get stores
@app.get("/stores")
def get_stores():
    return stores


# Get tables for a specific store
@app.get("/stores/{store_id}/tables")
def get_tables(store_id: int):
    try:
        store_data = get_store_table_data_from_gcs(store_id)
        return store_data
    except Exception:
        raise HTTPException(status_code=404, detail="Store not found")


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
            store_data = get_store_table_data_from_gcs(store_id)
            await client.send(json.dumps(store_data))
            await asyncio.sleep(10)  # Send updates every 10 seconds
    except asyncio.CancelledError:
        pass


def cancel_tasks():
    for clients in store_clients.values():
        for client in clients:
            client.cancel()


app.add_event_handler("shutdown", cancel_tasks)
