from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "X9lnNZSd4Fbed7f"
allowed_origins = ["http://localhost:3000"]

CORS(app, supports_credentials=True, resources={r"/*": {"origins": allowed_origins}})
socketio = SocketIO(app, cors_allowed_origins=allowed_origins, manage_session=False)


rooms = {}
user_sid_map = {}  # sid -> {"room": room, "name": name}


def generate_unique_code(length):
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))
        if code not in rooms:
            break
    return code


@app.route("/")
def say_hello():
    return "Hello, World!"


@app.route("/create", methods=["POST"])
def create():
    room_id = generate_unique_code(6)
    rooms[room_id] = {
        "members": [],
        "messages": [],
    }
    return jsonify({"room_id": room_id})


@app.route("/room/<string:id>", methods=["GET"])
def get_room(id):
    if id not in rooms:
        return jsonify({"error": "Room not found"}), 404
    return jsonify(rooms[id])


@socketio.on("join")
def handle_join(data):
    name = data.get("name")
    room = data.get("room")

    if room not in rooms:
        emit("error", {"message": "Room does not exist."})
        return

    join_room(room)
    user_sid_map[request.sid] = {"room": room, "name": name}

    if name not in rooms[room]["members"]:
        rooms[room]["members"].append(name)
        emit("user_joined", {"name": name}, room=room)
    else:
        emit("error", {"message": f"{name} is already in the room {room}"})


@socketio.on("message")
def handle_message(data):
    sid = request.sid
    user_info = user_sid_map.get(sid)

    if not user_info:
        emit("error", {"message": "User not in room."})
        return

    room = user_info["room"]
    name = user_info["name"]
    message = data.get("message")

    content = {"name": name, "message": message}
    rooms[room]["messages"].append(content)
    emit("response", content, room=room)
    print(f"{name} said: {message} in room {room}")


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    user_info = user_sid_map.pop(sid, None)

    if user_info:
        room = user_info["room"]
        name = user_info["name"]
        if room in rooms and name in rooms[room]["members"]:
            rooms[room]["members"].remove(name)
            emit("user_left", {"name": name}, room=room)
            print(f"{name} left room {room}")


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
