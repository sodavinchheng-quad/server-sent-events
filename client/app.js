let username = "";
let eventSource;
let chatBox = document.getElementById("chat-box");
let connectionStatus = document.getElementById("connection-status");

function connectToChat(event) {
  event.preventDefault(); // Prevent form submission from reloading the page
  username = document.getElementById("username").value.trim();
  if (username === "") {
    alert("Please enter a username");
    return;
  }

  // Show chat interface
  document.getElementById("username-section").style.display = "none";
  document.getElementById("message-section").style.display = "block";
  document.getElementById("username-display").textContent = username;

  // Change connection status to "connecting"
  connectionStatus.className = "disconnected";
  connectionStatus.innerText = "Connecting...";

  // Connect to the chat server via SSE
  eventSource = new EventSource(
    `http://127.0.0.1:8000/chat?username=${username}`
  );

  eventSource.onmessage = function (event) {
    const message = event.data;
    const messageElement = document.createElement("div");

    // Check if the message is a server message (i.e., a user joins or leaves the chat)
    if (
      message.includes("has joined the chat room") ||
      message.includes("has left the chat room")
    ) {
      messageElement.classList.add("server-message");
    } else if (message.includes(username)) {
      messageElement.classList.add("user-message");
    } else {
      messageElement.classList.add("other-user-message");
    }

    messageElement.classList.add("message-container");
    messageElement.innerHTML = message;
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
  };

  eventSource.onerror = function () {
    connectionStatus.className = "disconnected";
    connectionStatus.innerText = "Disconnected. Reconnecting...";
  };

  // Set status to connected once the SSE connection is established
  eventSource.onopen = function () {
    connectionStatus.className = "connected";
    connectionStatus.innerText = "Connected as " + username;
  };
}

function sendMessage(event) {
  event.preventDefault(); // Prevent form submission from reloading the page
  const message = document.getElementById("message").value.trim();
  if (message === "") return;

  fetch("http://127.0.0.1:8000/send_message", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, message }),
  });

  // Display the message locally for immediate feedback (user message)
  const messageElement = document.createElement("div");
  messageElement.classList.add("user-message", "message-container");
  messageElement.innerHTML = `<strong>${username}:</strong> ${message}`;
  chatBox.appendChild(messageElement);
  chatBox.scrollTop = chatBox.scrollHeight;
  document.getElementById("message").value = "";
}
