let apiUrl = "";
let eventSource = null; // Will hold the EventSource instance

// Load environment variables from env.json
async function loadEnv() {
  const response = await fetch(apiUrl + "env.json");
  const env = await response.json();
  apiUrl = env.API_URL;
}

// DOM Elements
const storeSearch = document.getElementById("store-search");
const storeSelect = document.getElementById("store-select");
const tableBody = document.getElementById("table-body");
const connectionStatusElem = document.getElementById("connection-status");
const selectedStoreDiv = document.getElementById("selected-store");
const storeNameSpan = document.getElementById("store-name");
const changeStoreButton = document.getElementById("change-store");

// API Endpoints
const storesApi = "/api/stores"; // Replace with your actual API
const tableStatusApi = (storeId) => `/api/stores/${storeId}/tables`; // Replace with your actual API

let stores = []; // Will hold the fetched stores

// Fetch and populate stores
async function fetchStores() {
  try {
    const response = await fetch(apiUrl + storesApi);
    stores = await response.json();
    populateStoreDropdown(stores);
  } catch (error) {
    console.error("Error fetching stores:", error);
  }
}

// Populate store dropdown
function populateStoreDropdown(stores) {
  storeSelect.innerHTML = ""; // Clear existing options
  stores.forEach((store) => {
    const option = document.createElement("option");
    option.value = store.id;
    option.textContent = store.name;
    storeSelect.appendChild(option);
  });
}

// Filter stores based on search input
storeSearch.addEventListener("input", (event) => {
  const keyword = event.target.value.toLowerCase();
  const filteredStores = stores.filter((store) =>
    store.name.toLowerCase().includes(keyword)
  );
  populateStoreDropdown(filteredStores);
});

// Fetch and display table status
async function fetchTableStatus(storeId) {
  try {
    const response = await fetch(apiUrl + tableStatusApi(storeId));
    const tables = await response.json();
    populateTableStatus(tables);
  } catch (error) {
    console.error("Error fetching table status:", error);
  }
}

// Populate table status
function populateTableStatus(tables) {
  tableBody.innerHTML = ""; // Clear existing rows
  tables.forEach((table) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${table.table_no}</td>
      <td class="${table.status}">${table.status}</td>
    `;
    tableBody.appendChild(row);
  });
}

// Set up Server-Sent Events
function setupSSE(storeId) {
  eventSource = new EventSource(apiUrl + `/api/events/${storeId}`);

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
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.message) {
      // Display the message in a popup (you can use a modal for a more styled popup)
      showPopup(data.message);
    } else {
      populateTableStatus(data);
    }
  };
}
// Hide store selection and show the selected store indicator
function handleStoreSelection(storeId, storeName) {
  document.querySelector(".dropdown").classList.add("hidden");
  selectedStoreDiv.classList.remove("hidden");
  storeNameSpan.textContent = storeName;

  // Fetch and display the table status
  fetchTableStatus(storeId);
  setupSSE(storeId);
}

// Show store selection again when changing the store
changeStoreButton.addEventListener("click", () => {
  document.querySelector(".dropdown").classList.remove("hidden");
  selectedStoreDiv.classList.add("hidden");
  tableBody.innerHTML = ""; // Clear table status
  eventSource.close(); // Close the SSE connection
  connectionStatusElem.textContent = "Disconnected";
  connectionStatusElem.classList.replace("connected", "disconnected");
  storeSelect.selectedIndex = -1; // Reset the selected store
});

// Modify the event listener for store selection
storeSelect.addEventListener("change", (event) => {
  const selectedOption = storeSelect.options[storeSelect.selectedIndex];
  if (selectedOption) {
    handleStoreSelection(selectedOption.value, selectedOption.textContent);
  }
});

// Helper function to get query parameters
function getQueryParams() {
  const params = new URLSearchParams(window.location.search);
  const storeId = params.get("store_id");
  return storeId;
}

// Automatically select store based on query parameter
async function checkForStoreInURL() {
  const storeId = getQueryParams();
  if (storeId) {
    try {
      // Ensure stores are loaded before checking
      if (stores.length === 0) {
        await fetchStores();
      }
      const store = stores.find((s) => s.id == storeId);
      if (store) {
        handleStoreSelection(store.id, store.name);
      } else {
        console.warn(`Store with ID ${storeId} not found.`);
      }
    } catch (error) {
      console.error("Error checking URL for store:", error);
    }
  }
}

// Initialize the app
loadEnv().then(async () => {
  await fetchStores();
  await checkForStoreInURL();
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
