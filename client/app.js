let selectedStore = null;
const storeSelectionDiv = document.getElementById("store-selection");
const tableStatusDiv = document.getElementById("table-status");
const storeListElem = document.getElementById("store-list");
const tableListElem = document.getElementById("table-list");
const tableStatusSelect = document.getElementById("table-status-select");
const connectionStatusElem = document.getElementById("connection-status");
const selectedStoreElem = document.getElementById("selected-store");

let apiUrl = "";

// Load environment variables from env.json
async function loadEnv() {
  const response = await fetch("env.json");
  const env = await response.json();
  apiUrl = env.API_URL;
}

// Load stores and display them as cards
async function loadStores() {
  const response = await fetch(`${apiUrl}/stores`);
  const stores = await response.json();
  stores.forEach((store) => {
    const storeCard = document.createElement("div");
    storeCard.classList.add("store-card");
    storeCard.innerHTML = `<h3>${store.name}</h3><p>${store.location}</p>`;
    storeCard.addEventListener("click", () => selectStore(store.id));
    storeListElem.appendChild(storeCard);
  });
}

// Select a store and load its table data
async function selectStore(storeId) {
  selectedStore = storeId;
  const response = await fetch(`${apiUrl}/stores/${storeId}/tables`);
  const tables = await response.json();

  // Show table status section
  storeSelectionDiv.style.display = "none";
  tableStatusDiv.style.display = "block";

  // Update the selected store indicator
  selectedStoreElem.textContent = `Selected Store: ${
    tables.length > 0 ? tables[0].store_name : "Unknown Store"
  }`;

  // Display tables
  tableListElem.innerHTML = ""; // Clear previous table list
  tables.forEach((table) => {
    const tableItem = document.createElement("div");
    tableItem.classList.add("table-item", table.status); // Set initial status class
    tableItem.dataset.tableId = table.id;
    tableItem.innerHTML = `
      <p>Table ${table.id}</p>
      <span class="status">${table.status}</span>
    `;
    tableItem.addEventListener("click", () => updateTableStatus(table.id));
    tableListElem.appendChild(tableItem);
  });

  // Connect to SSE for real-time updates
  connectSSE(storeId);
}

// Connect to SSE for real-time updates
function connectSSE(storeId) {
  const eventSource = new EventSource(`${apiUrl}/events/${storeId}`);

  // Handle SSE connection error
  eventSource.onerror = function () {
    connectionStatusElem.textContent = "Disconnected";
    connectionStatusElem.classList.replace("connected", "disconnected");
  };

  // When the connection opens, update status to connected
  eventSource.onopen = function () {
    connectionStatusElem.textContent = "Connected";
    connectionStatusElem.classList.replace("disconnected", "connected");
  };

  // Listen for messages
  eventSource.onmessage = function (event) {
    const data = JSON.parse(event.data);

    if (data.message) {
      // Display the message in a popup (you can use a modal for a more styled popup)
      showPopup(data.message);
    } else {
      updateTableList(data);
    }
  };
}

// Update table statuses in real-time when the event is received
function updateTableList(tables) {
  // Iterate over the tables and update the corresponding elements
  tables.forEach((table) => {
    const tableElement = document.querySelector(
      `.table-item[data-table-id="${table.id}"]`
    );
    if (tableElement) {
      // Update the table status and apply the correct class
      const statusElement = tableElement.querySelector(".status");
      tableElement.classList.remove("available", "reserved", "occupied");
      tableElement.classList.add(table.status);
      statusElement.textContent = table.status;
    }
  });
}

// Handle table status change from the select dropdown
function updateTableStatus(tableId) {
  const newStatus = tableStatusSelect.value;

  if (!selectedStore) {
    alert("No store selected!");
    return;
  }

  // Send update request to the server for the specific table and store
  fetch(`${apiUrl}/stores/${selectedStore}/tables/${tableId}/update`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status: newStatus }),
  })
    .then((response) => {
      if (response.ok) {
        console.log("Table status updated successfully");
      } else {
        console.error("Error updating table status");
      }
    })
    .catch((error) => {
      console.error("Error updating status:", error);
    });
}

// Initialize the app
loadEnv().then(() => {
  loadStores();
});

// Show a popup with the received message
function showPopup(message) {
  // Create a simple popup or modal
  const popup = document.createElement("div");
  popup.classList.add("popup");
  popup.innerHTML = `
    <div class="popup-content">
      <p>${message}</p>
      <button onclick="closePopup()">Close</button>
    </div>
  `;
  document.body.appendChild(popup);
}

// Close the popup
function closePopup() {
  const popup = document.querySelector(".popup");
  if (popup) {
    popup.remove();
  }
}
