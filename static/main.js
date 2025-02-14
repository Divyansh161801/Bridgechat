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

    // Handle user leaving the room
    window.addEventListener('beforeunload', () => {
        socket.emit('leave', { room: room });
    });
});
