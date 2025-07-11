const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const socket = io();

let role = "spectator";

socket.on('role', (data) => {
    role = data;
});

socket.on('state', (data) => {
    const { ball, paddles, score } = data;

    ctx.clearRect(0, 0, 600, 400);

    // draw paddles
    ctx.fillStyle = 'white';
    ctx.fillRect(10, paddles.left, 10, 80);
    ctx.fillRect(580, paddles.right, 10, 80);

    // draw ball
    ctx.beginPath();
    ctx.arc(ball.x, ball.y, 8, 0, Math.PI * 2);
    ctx.fill();

    // draw score
    ctx.fillStyle = 'white';
    ctx.font = '20px Arial';
    ctx.fillText(`Left: ${score.left}`, 20, 20);
    ctx.fillText(`Right: ${score.right}`, 480, 20);
});

canvas.addEventListener('mousemove', (e) => {
    if (role === "left" || role === "right") {
        const rect = canvas.getBoundingClientRect();
        const y = e.clientY - rect.top - 40;
        socket.emit('paddle_move', { y });
    }
});


function resetGame() {
    socket.emit('reset');
}