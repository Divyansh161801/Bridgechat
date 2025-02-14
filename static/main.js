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

    // Receive message from server and display it
    socket.on('message', (message) => {
        const li = document.createElement('li');
        li.textContent = message;
        messageList.appendChild(li);
    });

    // Send message to WebSocket & Flask
    messageForm.addEventListener('submit', (event) => {
        event.preventDefault(); // Prevent page refresh

        const message = messageInput.value.trim();
        if (!message) return;

        // Send message via WebSocket
        socket.emit('message', { room: room, message: message });

        // Send message to Flask backend
        const formData = new FormData(messageForm);
        fetch('/chatroom', {
            method: 'POST',
            body: formData
        }).then(response => response.text())
          .then(data => console.log("Message sent to Flask:", data))
          .catch(error => console.error("Error sending message:", error));

        messageInput.value = ''; // Clear input after sending
    });


from Flask (Stored in Google Drive)**
    fetch(`/get_messages?room=${room}`)
        .then(response => response.json())
        .then(data => {
            data.messages.forEach(msg => {
                displayMessage(msg.user, msg.message);
            });
        })
        .catch(error => console.error("Error fetching messages:", error));

    // **2️⃣ Receive new messages from the server (Real-Time Update)**
    socket.on('message', (data) => {
        displayMessage(data.user, data.message);
    });

    // **3️⃣ Send a new message**
    messageForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const message = messageInput.value.trim();

        if (message) {
            socket.emit('message', { room: room, message: message });

            // **Update UI instantly**
            displayMessage(username, message);
            messageInput.value = '';
        }
    });

    // **4️⃣ Function to display messages in chat UI**
    function displayMessage(user, message) {
        const msgElement = document.createElement('p');
        msgElement.innerHTML = `<strong>${user}:</strong> ${message}`;
        messageList.appendChild(msgElement);
        }
                

    
    // Handle user leaving the room
    window.addEventListener('beforeunload', () => {
        socket.emit('leave', { room: room });
    });
});
