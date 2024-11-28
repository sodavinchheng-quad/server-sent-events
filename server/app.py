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
periodic_task: asyncio.Task | None = None


def get_total_client_count():
    return sum(len(clients) for clients in store_clients.values())


# Get stores
@app.get("/stores")
def get_stores():
    return stores


@app.get("/check_status")
def check_status():
    return {
        "store_clients": {store_id: len(clients) for store_id, clients in store_clients.items()},
        "periodic_task": periodic_task is not None,
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
    global periodic_task

    if store_id not in store_clients:
        raise HTTPException(status_code=404, detail="Store not found")

    client_queue = asyncio.Queue()
    store_clients[store_id].append(client_queue)

    async def event_stream():
        global periodic_task

        try:
            while True:
                message = await client_queue.get()
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            store_clients[store_id].remove(client_queue)
            # if no more clients, cancel the periodic task
            if get_total_client_count() == 0:
                cancel_periodic_task()

    # Start the periodic task if not already running
    if periodic_task is None:
        periodic_task = asyncio.create_task(periodic_status_update())

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def cancel_periodic_task():
    global periodic_task
    if periodic_task:
        periodic_task.cancel()
        periodic_task = None


# Periodic status update task
async def periodic_status_update():
    try:
        while True:
            for store_id, clients in store_clients.items():
                for client in clients:
                    await client.put(json.dumps(tables[store_id]))
            await asyncio.sleep(60)  # Send updates every 60 seconds
    except asyncio.CancelledError:
        if get_total_client_count() == 0:
            cancel_periodic_task()  # Cleanup when task is canceled

app.add_event_handler("shutdown", cancel_periodic_task)
