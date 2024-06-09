document.addEventListener('DOMContentLoaded', () => {
    const socket = io.connect('https://' + document.domain + ':' + location.port);

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

setInterval(() => {
    fetch('/keep-alive', {
        method: 'GET',
        credentials: 'same-origin'  // Include this if necessary
    });
}, 600000);  // 600000 milliseconds = 10 minutes
