from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import random
import string
import time
import threading

DEFAULT_ROOM_ID = "DEFAULT"
ROOM_TTL_SECONDS = 15
CLEANUP_INTERVAL_SECONDS = 5

rooms = {}
rooms_lock = threading.Lock()


def log_event(message: str):
    print(f"[SERVER] {message}")


def now_ts() -> int:
    return int(time.time())


def make_room_code(length=4):
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=length))
        if code != DEFAULT_ROOM_ID and code not in rooms:
            return code


def check_winner(board):
    wins = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]

    for a, b, c in wins:
        if board[a] != "" and board[a] == board[b] == board[c]:
            return board[a]

    if all(cell != "" for cell in board):
        return "draw"

    return None


def new_room(room_id: str, is_default: bool = False):
    return {
        "room_id": room_id,
        "is_default": is_default,
        "board": [""] * 9,
        "players": {
            "X": None,
            "O": None,
        },
        "turn": "X",
        "winner": None,
        "status": "waiting",
        "score": {
            "X": 0,
            "O": 0,
            "draws": 0,
        },
        "sessions": {},
        "created_at": now_ts(),
        "updated_at": now_ts(),
    }


def ensure_default_room():
    with rooms_lock:
        if DEFAULT_ROOM_ID not in rooms:
            rooms[DEFAULT_ROOM_ID] = new_room(DEFAULT_ROOM_ID, is_default=True)
            log_event(f"Created default room {DEFAULT_ROOM_ID}")


def active_sessions(room):
    cutoff = now_ts() - ROOM_TTL_SECONDS
    return {
        session_id: meta
        for session_id, meta in room["sessions"].items()
        if meta["last_seen"] >= cutoff
    }


def room_player_count(room):
    count = 0
    if room["players"]["X"] is not None:
        count += 1
    if room["players"]["O"] is not None:
        count += 1
    return count


def room_client_types(room):
    types = []
    for _, meta in active_sessions(room).items():
        ct = meta.get("client_type", "unknown")
        if ct not in types:
            types.append(ct)
    return types


def room_ready(room):
    return room["players"]["X"] is not None and room["players"]["O"] is not None


def room_summary(room):
    return {
        "room_id": room["room_id"],
        "is_default": room["is_default"],
        "players_count": room_player_count(room),
        "capacity": 2,
        "status": room["status"],
        "ready": room_ready(room),
        "turn": room["turn"],
        "winner": room["winner"],
        "client_types": room_client_types(room),
        "score": room["score"],
        "slots": {
            "X": room["players"]["X"],
            "O": room["players"]["O"],
        },
    }


def reset_room_board(room):
    room["board"] = [""] * 9
    room["turn"] = "X"
    room["winner"] = None
    room["status"] = "playing" if room_ready(room) else "waiting"
    room["updated_at"] = now_ts()


def update_score_if_finished(room):
    winner = room["winner"]
    if winner == "X":
        room["score"]["X"] += 1
    elif winner == "O":
        room["score"]["O"] += 1
    elif winner == "draw":
        room["score"]["draws"] += 1


def remove_expired_sessions_and_cleanup():
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        cutoff = now_ts() - ROOM_TTL_SECONDS

        with rooms_lock:
            room_ids = list(rooms.keys())

            for room_id in room_ids:
                room = rooms.get(room_id)
                if not room:
                    continue

                expired_session_ids = [
                    session_id
                    for session_id, meta in room["sessions"].items()
                    if meta["last_seen"] < cutoff
                ]

                for session_id in expired_session_ids:
                    meta = room["sessions"].pop(session_id, None)
                    if not meta:
                        continue

                    player = meta["player"]
                    if room["players"].get(player) == session_id:
                        room["players"][player] = None
                        log_event(
                            f"Session expired in room {room_id}: player {player} ({meta['client_type']}) disconnected"
                        )

                if not room_ready(room):
                    room["status"] = "waiting"

                if room["is_default"]:
                    if room_player_count(room) == 0:
                        room["board"] = [""] * 9
                        room["turn"] = "X"
                        room["winner"] = None
                        room["status"] = "waiting"
                    continue

                if room_player_count(room) == 0:
                    del rooms[room_id]
                    log_event(f"Destroyed empty room {room_id}")


cleanup_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cleanup_thread
    ensure_default_room()

    if cleanup_thread is None:
        cleanup_thread = threading.Thread(
            target=remove_expired_sessions_and_cleanup,
            daemon=True,
        )
        cleanup_thread.start()

    yield


app = FastAPI(title="TicTacToe Multiplayer API", lifespan=lifespan)


class CreateRoomRequest(BaseModel):
    session_id: str
    client_type: str


class JoinRequest(BaseModel):
    room_id: str = DEFAULT_ROOM_ID
    session_id: str
    client_type: str


class MoveRequest(BaseModel):
    room_id: str
    session_id: str
    position: int


class ResetRequest(BaseModel):
    room_id: str
    session_id: str


class NewGameRequest(BaseModel):
    room_id: str
    session_id: str


class HeartbeatRequest(BaseModel):
    room_id: str
    session_id: str
    client_type: str


class LeaveRequest(BaseModel):
    room_id: str
    session_id: str


@app.get("/")
def root():
    ensure_default_room()
    return {"message": "TicTacToe server is running", "default_room": DEFAULT_ROOM_ID}


@app.get("/rooms")
def list_rooms():
    ensure_default_room()
    with rooms_lock:
        return {
            "default_room": DEFAULT_ROOM_ID,
            "rooms": [room_summary(room) for room in rooms.values()]
        }


@app.post("/create_room")
def create_room(req: CreateRoomRequest):
    client_type = req.client_type.lower()
    if client_type not in {"cli", "gui", "android"}:
        raise HTTPException(status_code=400, detail="Invalid client_type")

    with rooms_lock:
        room_id = make_room_code()
        room = new_room(room_id, is_default=False)
        rooms[room_id] = room

        room["players"]["X"] = req.session_id
        room["sessions"][req.session_id] = {
            "player": "X",
            "client_type": client_type,
            "last_seen": now_ts(),
        }
        room["status"] = "waiting"
        room["updated_at"] = now_ts()

        log_event(f"Created room {room_id}; player X joined via {client_type}")
        return {"room_id": room_id, "player": "X"}


@app.post("/join_room")
def join_room(req: JoinRequest):
    room_id = (req.room_id or DEFAULT_ROOM_ID).upper()

    with rooms_lock:
        room = rooms.get(room_id)
        if not room:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

        client_type = req.client_type.lower()
        if client_type not in {"cli", "gui", "android"}:
            raise HTTPException(status_code=400, detail="Invalid client_type")

        if req.session_id in room["sessions"]:
            meta = room["sessions"][req.session_id]
            meta["last_seen"] = now_ts()
            meta["client_type"] = client_type
            return {"room_id": room_id, "player": meta["player"]}

        if room["players"]["X"] is None:
            assigned = "X"
            room["players"]["X"] = req.session_id
        elif room["players"]["O"] is None:
            assigned = "O"
            room["players"]["O"] = req.session_id
        else:
            raise HTTPException(status_code=400, detail=f"Room {room_id} is full")

        room["sessions"][req.session_id] = {
            "player": assigned,
            "client_type": client_type,
            "last_seen": now_ts(),
        }

        room["status"] = "playing" if room_ready(room) else "waiting"
        room["updated_at"] = now_ts()

        log_event(f"Joined room {room_id}; player {assigned} via {client_type}")
        return {"room_id": room_id, "player": assigned}


@app.post("/heartbeat")
def heartbeat(req: HeartbeatRequest):
    room_id = req.room_id.upper()

    with rooms_lock:
        room = rooms.get(room_id)
        if not room:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

        meta = room["sessions"].get(req.session_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Session not found in room")

        meta["last_seen"] = now_ts()
        meta["client_type"] = req.client_type.lower()
        room["updated_at"] = now_ts()

        return {"ok": True, "room": room_summary(room)}


@app.post("/leave")
def leave(req: LeaveRequest):
    room_id = req.room_id.upper()

    with rooms_lock:
        room = rooms.get(room_id)
        if not room:
            return {"ok": True}

        meta = room["sessions"].pop(req.session_id, None)
        if meta:
            player = meta["player"]
            if room["players"].get(player) == req.session_id:
                room["players"][player] = None
            log_event(f"Left room {room_id}; player {player} ({meta['client_type']}) exited")

        room["status"] = "playing" if room_ready(room) else "waiting"
        room["updated_at"] = now_ts()

        if not room["is_default"] and room_player_count(room) == 0:
            del rooms[room_id]
            log_event(f"Destroyed empty room {room_id}")

        return {"ok": True}


@app.get("/state/{room_id}")
def get_state(room_id: str):
    with rooms_lock:
        room = rooms.get(room_id.upper())
        if not room:
            raise HTTPException(status_code=404, detail=f"Room {room_id.upper()} not found")

        return {
            **room,
            "players_count": room_player_count(room),
            "ready": room_ready(room),
            "client_types": room_client_types(room),
        }


@app.post("/move")
def make_move(req: MoveRequest):
    room_id = req.room_id.upper()

    with rooms_lock:
        room = rooms.get(room_id)
        if not room:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

        session = room["sessions"].get(req.session_id)
        if not session:
            raise HTTPException(status_code=403, detail="Session not in room")

        player = session["player"]

        if room["status"] != "playing":
            raise HTTPException(status_code=400, detail="Game is not ready yet")

        if room["winner"] is not None:
            raise HTTPException(status_code=400, detail="Game already finished")

        if player != room["turn"]:
            raise HTTPException(status_code=400, detail="Not your turn")

        if req.position < 0 or req.position > 8:
            raise HTTPException(status_code=400, detail="Position must be between 0 and 8")

        if room["board"][req.position] != "":
            raise HTTPException(status_code=400, detail="Cell already taken")

        room["board"][req.position] = player

        result = check_winner(room["board"])
        if result is not None:
            room["winner"] = result
            room["status"] = "finished"
            update_score_if_finished(room)
        else:
            room["turn"] = "O" if room["turn"] == "X" else "X"

        room["updated_at"] = now_ts()
        return room


@app.post("/reset")
def reset_game(req: ResetRequest):
    room_id = req.room_id.upper()

    with rooms_lock:
        room = rooms.get(room_id)
        if not room:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

        if req.session_id not in room["sessions"]:
            raise HTTPException(status_code=403, detail="Session not in room")

        reset_room_board(room)
        return room


@app.post("/new_game")
def new_game(req: NewGameRequest):
    room_id = req.room_id.upper()

    with rooms_lock:
        room = rooms.get(room_id)
        if not room:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

        if req.session_id not in room["sessions"]:
            raise HTTPException(status_code=403, detail="Session not in room")

        reset_room_board(room)
        return room