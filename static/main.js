document.addEventListener('DOMContentLoaded', () => {
    const protocol = location.protocol === 'https:' ? 'wss://' : 'ws://';
    const socket = io.connect('https://bridgechat-hdbq.onrender.com', {
    transports: ['websocket', 'polling'],
    upgrade: true
});

    // Join room event
    const username = '{{ current_user.username }}';
    const room = '{{ room }}';

    console.log('Joining room:', room, 'with username:', username);
    socket.emit('join', {username: username, room: room});

    // Listen for messages
    socket.on('message', data => {
        console.log('Received message:', data);
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML += `<p><strong>${data.username}:</strong> ${data.message}</p>`;
    });

    // Listen for join notifications
    socket.on('join', data => {
        console.log('Join notification:', data);
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML += `<p>${data.username} has joined the room.</p>`;
    });

    // Send message
    const form = document.getElementById('messageForm');
    form.addEventListener('submit', event => {
        event.preventDefault();
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value;
        console.log('Sending message:', message);
        socket.emit('message', {username: username, room: room, message: message});
        messageInput.value = '';
    });
});

const socket = io('https://bridgechat-hdbq.onrender.com');

socket.on('connect', function() {
    console.log('Connected to the server');
});

socket.on('disconnect', function() {
    console.log('Disconnected from the server');
});

// Define additional socket event handlers

setInterval(() => {
    fetch('/keep-alive', {
        method: 'GET',
        credentials: 'same-origin'  // Include this if necessary
    });
}, 600000);  // 600000 milliseconds = 10 minutes
