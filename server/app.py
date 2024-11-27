from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
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

# Mock store and table data
stores = [
    {"id": 1, "name": "Store A", "location": "Location A"},
    {"id": 2, "name": "Store B", "location": "Location B"},
]

tables = {
    1: [
        {"id": 1, "store_name": "Store A", "status": "available"},
        {"id": 2, "store_name": "Store A", "status": "reserved"},
    ],
    2: [
        {"id": 1, "store_name": "Store B", "status": "occupied"},
        {"id": 2, "store_name": "Store B", "status": "available"},
    ],
}

# Store clients (to broadcast messages)
store_clients: Dict[int, List[asyncio.Queue]] = {1: [], 2: []}

# Periodic tasks
periodic_tasks: Dict[int, asyncio.Task] = {}


# Get stores
@app.get("/stores")
def get_stores():
    return stores


@app.get("/check_status")
def check_status():
    return {
        "store_clients": {store_id: len(clients) for store_id, clients in store_clients.items()},
        "periodic_tasks": list(periodic_tasks.keys()),
    }


# Get tables for a specific store
@app.get("/stores/{store_id}/tables")
def get_tables(store_id: int):
    if store_id not in tables:
        raise HTTPException(status_code=404, detail="Store not found")
    return tables[store_id]


# Update table status for a specific table in a specific store
@app.post("/stores/{store_id}/tables/{table_id}/update")
async def update_table_status(store_id: int, table_id: int, request: Request):
    data: Dict = await request.json()
    status = data.get("status")

    if store_id not in tables:
        raise HTTPException(status_code=404, detail="Store not found")

    table = next((t for t in tables[store_id] if t["id"] == table_id), None)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    table["status"] = status
    return {"message": "Status updated"}


# Send a message to all clients connected to a specific store via SSE
@app.post("/stores/{store_id}/push-message")
async def push_message(store_id: int, request: Request):
    data: Dict = await request.json()
    message = data.get("message")

    if not any(store["id"] == store_id for store in stores):
        raise HTTPException(status_code=404, detail="Store not found")

    for client in store_clients[store_id]:
        await client.put(json.dumps({"message": message}))

    return {"message": "Message pushed"}


# SSE for real-time updates (listening to store table status changes)
@app.get("/events/{store_id}")
async def sse_events(store_id: int):
    if store_id not in store_clients:
        raise HTTPException(status_code=404, detail="Store not found")

    client_queue = asyncio.Queue()
    store_clients[store_id].append(client_queue)

    async def event_stream():
        try:
            while True:
                message = await client_queue.get()
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            store_clients[store_id].remove(client_queue)
            # if no more clients, cancel the periodic task
            if not store_clients[store_id]:
                periodic_tasks[store_id].cancel()

    # Start the periodic task if not already running
    if store_id not in periodic_tasks:
        periodic_tasks[store_id] = asyncio.create_task(
            periodic_status_update(store_id))

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Periodic status update task
async def periodic_status_update(store_id: int):
    try:
        while True:
            if store_clients[store_id]:  # Only run if there are active clients
                data = json.dumps(tables[store_id])
                for client in store_clients[store_id]:
                    await client.put(data)
            await asyncio.sleep(60)  # Send updates every 60 seconds
    except asyncio.CancelledError:
        del periodic_tasks[store_id]  # Cleanup when task is canceled


async def cleanup():
    # Cancel all periodic tasks on shutdown
    for task in list(periodic_tasks.values()):
        task.cancel()

app.add_event_handler("shutdown", cleanup)
