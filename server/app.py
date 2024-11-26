from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import List

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionary to keep track of all connected clients (each client is identified by their username)
# List of dictionaries with username and corresponding queue
clients: List[dict] = []


@app.get("/chat")
async def chat(request: Request, username: str):
    """
    Endpoint for SSE. Each client connects to this endpoint and receives messages in real-time.
    """
    # Create a queue for each connected client
    queue = asyncio.Queue()

    # Add the queue and username to the list of clients
    clients.append({"username": username, "queue": queue})

    # Inform the other clients about the new connection
    await broadcast_message(f"data: {username} has joined the chat room!\n\n")

    async def event_stream():
        try:
            while True:
                message = await queue.get()  # Wait for a new message
                yield message  # Send it to the client
        except asyncio.CancelledError:
            # When the connection is closed (user disconnects), we remove the client from the list
            clients.remove({"username": username, "queue": queue})
            await broadcast_message(f"data: {username} has left the chat room.\n\n")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/send_message")
async def send_message(request: Request):
    """
    Endpoint to send a message to all connected clients, excluding the sender.
    """
    data = await request.json()
    username = data.get("username")
    message = data.get("message")

    if not username or not message:
        return {"error": "Username and message are required."}

    # Create a message to broadcast
    broadcast_message = f"data: {username}: {message}\n\n"

    # Broadcast the message to all connected clients, excluding the sender
    for client in clients:
        if client["username"] != username:
            # Push the message into each client's queue
            await client["queue"].put(broadcast_message)

    return {"message": "Message sent to all clients (excluding the sender)."}


async def broadcast_message(message: str):
    """
    Broadcast a message to all clients.
    """
    for client in clients:
        # Push the message into each client's queue
        await client["queue"].put(message)


@app.get("/stream")
async def stream(request: Request):
    """
    SSE stream that sends a 'ping' message to all clients every 5 seconds.
    """
    async def event_stream():
        while True:
            try:
                await asyncio.sleep(5)
                yield "data: ping\n\n"
            except asyncio.CancelledError:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")
