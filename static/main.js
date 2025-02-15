document.addEventListener('DOMContentLoaded', () => {
    const socket = io("https://bridgechat-hdbq.onrender.com", {
        transports: ["websocket"]
    });

    const messageForm = document.getElementById('messageForm');  
    const messageInput = document.getElementById('messageInput');  
    const messageList = document.getElementById('messages');  

    // Access room and username from the global window object
    const room = window.chatRoom;
    const username = window.chatUsername;

    // Join room
    socket.emit('join', { room: room });

    // **1️⃣ Listen for new messages and update UI instantly**
    socket.on('message', (data) => {
        displayMessage(data.user, data.message);
    });

    // **2️⃣ Send message (Instant for UI + WebSocket, Async for Drive)**
    messageForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        // **Send message via WebSocket for real-time update**
        socket.emit('message', { room: room, user: username, message: message });

        // **Update UI instantly for sender**
        displayMessage(username, message);

        // **Send message to Flask backend for Google Drive storage (Async)**
        fetch('/chatroom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room: room, user: username, message: message })
        }).then(response => response.text())
          .then(data => console.log("Message saved in Drive:", data))
          .catch(error => console.error("Error saving message:", error));

        messageInput.value = ''; // Clear input after sending
    });

    // **3️⃣ Fetch existing messages from Google Drive (Only once)**
    fetch(`/get_messages?room=${room}`)
        .then(response => response.json())
        .then(data => {
            data.messages.forEach(msg => {
                displayMessage(msg.user, msg.message);
            });
        })
        .catch(error => console.error("Error fetching messages:", error));

    // **4️⃣ Function to display messages in chat UI**
    function displayMessage(user, message) {
        const msgElement = document.createElement('p');
        msgElement.innerHTML = `<strong>${user}:</strong> ${message}`;
        messageList.appendChild(msgElement);
    }

    // **5️⃣ Handle user leaving the room**
    window.addEventListener('beforeunload', () => {
        socket.emit('leave', { room: room });
    });
});
