document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    const room = document.getElementById('room-name').textContent;
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const messageList = document.getElementById('message-list');

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
