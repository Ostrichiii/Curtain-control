from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
import RPi.GPIO as GPIO
import time

# GPIO pin assignments
RELAY_UP = 23
RELAY_STOP = 24
RELAY_DOWN = 25
LIMIT_TOP = 27
LIMIT_BOTTOM = 22

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_UP, GPIO.OUT)
GPIO.setup(RELAY_STOP, GPIO.OUT)
GPIO.setup(RELAY_DOWN, GPIO.OUT)
GPIO.setup(LIMIT_TOP, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(LIMIT_BOTTOM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Initial pin state
state = {
    "relay": {"up": False, "stop": True, "down": False},  # Default: stopped
    "limit": {"top": False, "bottom": False},
}

# Flask + SocketIO setup
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)

@socketio.on("connect")
def handle_connect():
    print("✅ Client connected")
    emit("status", state)

@socketio.on("command")
def handle_command(data):
    cmd = data.get("action")
    print(f"📥 Received command: {cmd}")

    # Reset all relays before setting the new one
    GPIO.output(RELAY_UP, GPIO.LOW)
    GPIO.output(RELAY_STOP, GPIO.LOW)
    GPIO.output(RELAY_DOWN, GPIO.LOW)

    if cmd == "up":
        GPIO.output(RELAY_UP, GPIO.HIGH)
        state["relay"] = {"up": True, "stop": False, "down": False}
        emit("log", "Calling server: move up", broadcast=True)
    elif cmd == "down":
        GPIO.output(RELAY_DOWN, GPIO.HIGH)
        state["relay"] = {"up": False, "stop": False, "down": True}
        emit("log", "Calling server: move down", broadcast=True)
    elif cmd == "stop":
        GPIO.output(RELAY_STOP, GPIO.HIGH)
        state["relay"] = {"up": False, "stop": True, "down": False}
        emit("log", "Calling server: stop", broadcast=True)
    else:
        emit("log", f"⚠️ Unknown command: {cmd}", broadcast=True)
        return

    # Read limit switch states
    state["limit"]["top"] = GPIO.input(LIMIT_TOP)
    state["limit"]["bottom"] = GPIO.input(LIMIT_BOTTOM)

    # Emit status and GPIO states
    log_gpio_states()
    socketio.emit("status", state)
    emit("log", "✅ Server responded: OK", broadcast=True)

def log_gpio_states():
    # Helper: Send log lines for each GPIO used
    logs = [
        f"GPIO {RELAY_UP} relay up -> {GPIO.input(RELAY_UP)}",
        f"GPIO {RELAY_STOP} relay stop -> {GPIO.input(RELAY_STOP)}",
        f"GPIO {RELAY_DOWN} relay down -> {GPIO.input(RELAY_DOWN)}",
        f"GPIO {LIMIT_TOP} top limit -> {GPIO.input(LIMIT_TOP)}",
        f"GPIO {LIMIT_BOTTOM} bottom limit -> {GPIO.input(LIMIT_BOTTOM)}"
    ]
    for line in logs:
        emit("log", line, broadcast=True)

if __name__ == "__main__":
    print("🚀 Starting server at http://0.0.0.0:5050")
    socketio.run(app, host="0.0.0.0", port=5050)