const express = require("express");
const cors = require("cors");

const app = express();
const PORT = 8000;

// Enable CORS for all routes
app.use(cors());

// Store connected clients (WebSocket-like functionality with SSE)
let clients = [];

// Endpoint for sending messages
app.use(express.json());

// Send a message to all clients except the sender
app.post("/send_message", (req, res) => {
  const { username, message } = req.body;

  // Broadcast message to all connected clients except the sender
  clients.forEach((client) => {
    if (client.username !== username) {
      client.res.write(`data: ${username}: ${message}\n\n`);
    }
  });

  res.status(200).send("Message sent");
});

// SSE endpoint for broadcasting messages to clients
app.get("/chat", (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  // Add the client to the list
  const username = req.query.username;
  clients.push({ username, res });

  // Send the same message when a user joins or leaves the chat
  const joinLeaveMessage = `${username} has joined the chat room.`;

  // Notify other users about the new user
  clients.forEach((client) => {
    if (client.username !== username) {
      client.res.write(`data: ${joinLeaveMessage}\n\n`);
    }
  });

  // Notify the new user that they're connected
  res.write(`data: ${joinLeaveMessage}\n\n`);

  // Clean up when client disconnects
  req.on("close", () => {
    clients = clients.filter((client) => client.res !== res);
    clients.forEach((client) => {
      client.res.write(`data: ${username} has left the chat room.\n\n`);
    });
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
