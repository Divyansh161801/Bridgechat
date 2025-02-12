document.addEventListener('DOMContentLoaded', () => {
    const socket = io("https://bridgechat-hdbq.onrender.com", {
    transports: ["websocket"]
});const messageForm = document.getElementById('messageForm');  // Fixed ID
    const messageInput = document.getElementById('messageInput'); // Fixed ID
    const messageList = document.getElementById('messages'); // Fixed ID
    
        // Access room and username from the global window object
    const room = window.chatRoom;
    const username = window.chatUsername

    // Join room
    socket.emit('join', { room: room });

    // Receive message from server
    socket.on('message', (message) => {
        const li = document.createElement('li');
        li.textContent = message;
        messageList.appendChild(li);
    });

    // Send message to server
    messageForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const message = messageInput.value;
        socket.emit('message', { room: room, message: message });
        messageInput.value = '';
    });

    // Handle user leaving room
    window.addEventListener('beforeunload', () => {
        socket.emit('leave', { room: room });
    });
});
