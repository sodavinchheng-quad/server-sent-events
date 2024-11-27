const express = require("express");
const cors = require("cors");
const app = express();
const port = 8000;

// Enable CORS
app.use(cors());

// Mock store and table data
const stores = [
  { id: 1, name: "Store A", location: "Location A" },
  { id: 2, name: "Store B", location: "Location B" },
];

const tables = {
  1: [
    { id: 1, store_name: "Store A", status: "available" },
    { id: 2, store_name: "Store A", status: "reserved" },
  ],
  2: [
    { id: 1, store_name: "Store B", status: "occupied" },
    { id: 2, store_name: "Store B", status: "available" },
  ],
};

// Store clients (this will be used to broadcast messages)
const storeClients = {
  1: [],
  2: [],
};

// Get stores
app.get("/stores", (req, res) => {
  res.json(stores);
});

// Get tables for a specific store
app.get("/stores/:storeId/tables", (req, res) => {
  const storeId = req.params.storeId;
  res.json(tables[storeId]);
});

// Update table status for a specific table in a specific store
app.post(
  "/stores/:storeId/tables/:tableId/update",
  express.json(),
  (req, res) => {
    const storeId = req.params.storeId;
    const tableId = req.params.tableId;
    const { status } = req.body;

    // Check if the store and table exist
    if (!tables[storeId]) {
      return res.status(404).send("Store not found");
    }

    const table = tables[storeId].find(
      (table) => table.id === parseInt(tableId)
    );

    if (!table) {
      return res.status(404).send("Table not found");
    }

    // Update the status of the specific table
    table.status = status;

    // Send the updated table data back
    res.status(200).send("Status updated");
  }
);

// Send a message to all clients connected to a specific store via SSE
app.post("/stores/:storeId/push-message", express.json(), (req, res) => {
  const storeId = req.params.storeId;
  const { message } = req.body;

  // Check if the store exists
  if (!stores.find((store) => store.id === parseInt(storeId))) {
    return res.status(404).send("Store not found");
  }

  // Send the message to all clients connected to this store
  storeClients[storeId].forEach((client) => {
    client.write(`data: ${JSON.stringify({ message })}\n\n`);
  });

  res.status(200).send("Message pushed");
});

// SSE for real-time updates (listening to store table status changes)
app.get("/events/:storeId", (req, res) => {
  const storeId = req.params.storeId;

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  // Add client to the store's client list for real-time updates
  storeClients[storeId].push(res);

  // Function to send updated table statuses
  function sendTableStatusUpdates() {
    // Send updated data to client
    res.write(`data: ${JSON.stringify(tables[storeId])}\n\n`);
  }

  // Send updated table statuses every minute
  const intervalId = setInterval(sendTableStatusUpdates, 60000); // 60000ms = 1 minute

  // When the client disconnects, remove them from the store's client list
  req.on("close", () => {
    clearInterval(intervalId);
    const index = storeClients[storeId].indexOf(res);
    if (index !== -1) {
      storeClients[storeId].splice(index, 1);
    }
    res.end();
  });
});

app.listen(port, () => {
  console.log(`Server running on http://localhost:${port}`);
});
