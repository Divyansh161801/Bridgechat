document.addEventListener('DOMContentLoaded', () => {
    const socket = io.connect('http://' + document.domain + ':' + location.port);

    // Function to join the room
    function joinRoom(username, room) {
        console.log('Joining room:', room, 'with username:', username);
        socket.emit('join', {username: username, room: room});
    }

    // Function to handle incoming messages
    function handleMessage(data) {
        console.log('Received message:', data);
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML += `<p><strong>${data.username}:</strong> ${data.message}</p>`;
    }

    // Function to handle join notifications
    function handleJoin(data) {
        console.log('Join notification:', data);
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML += `<p>${data.username} has joined the room.</p>`;
    }

    // Listen for messages
    socket.on('message', handleMessage);

    // Listen for join notifications
    socket.on('join', handleJoin);

    // Send message
    const form = document.getElementById('messageForm');
    form.addEventListener('submit', event => {
        event.preventDefault();
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value;
        console.log('Sending message:', message);
        socket.emit('message', {username: window.chatUsername, room: window.chatRoom, message: message});
        messageInput.value = '';
    });

    // Periodic keep-alive request
    setInterval(() => {
        fetch('/keep-alive', {
            method: 'GET',
            credentials: 'same-origin'
        });
    }, 600000);  // 600000 milliseconds = 10 minutes

    // Initialize with dynamic data
    joinRoom(window.chatUsername, window.chatRoom);
});