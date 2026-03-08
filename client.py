#!/usr/bin/env python3

import argparse
import atexit
import requests
import threading
import time
import uuid
import tkinter as tk
from tkinter import ttk, messagebox

DEFAULT_REMOTE_URL = "https://tictactoe-multiplayer-engine.onrender.com"
DEFAULT_LOCAL_URL = "http://127.0.0.1:8000"
DEFAULT_BASE_URL = DEFAULT_REMOTE_URL
DEFAULT_SERVER_CHOICE = "remote"
DEFAULT_MODE = "gui"
DEFAULT_ROOM_ID = "DEFAULT"


def friendly_error(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            data = exc.response.json()
            detail = data.get("detail")
            if isinstance(detail, str):
                return detail
            if isinstance(detail, list):
                parts = []
                for item in detail:
                    loc = ".".join(str(x) for x in item.get("loc", []))
                    msg = item.get("msg", "validation error")
                    parts.append(f"{loc}: {msg}")
                return "; ".join(parts)
        except Exception:
            pass
        return f"HTTP {exc.response.status_code}: {exc.response.text}"
    return str(exc)


class TicTacToeClient:
    def __init__(self, base_url, client_type):
        self.base_url = base_url.rstrip("/")
        self.client_type = client_type
        self.session_id = str(uuid.uuid4())

        self.room_id = ""
        self.player = ""
        self.state = None

        self.lock = threading.Lock()
        atexit.register(self.safe_leave)

    def list_rooms(self):
        r = requests.get(f"{self.base_url}/rooms", timeout=5)
        r.raise_for_status()
        return r.json()

    def create_room(self):
        r = requests.post(
            f"{self.base_url}/create_room",
            json={
                "session_id": self.session_id,
                "client_type": self.client_type,
            },
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        with self.lock:
            self.room_id = data["room_id"]
            self.player = data["player"]
        return data

    def join_room(self, room_id=DEFAULT_ROOM_ID):
        r = requests.post(
            f"{self.base_url}/join_room",
            json={
                "room_id": room_id.upper(),
                "session_id": self.session_id,
                "client_type": self.client_type,
            },
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        with self.lock:
            self.room_id = data["room_id"]
            self.player = data["player"]
        return data

    def auto_join_default(self):
        rooms_data = self.list_rooms()
        default_room = rooms_data.get("default_room", DEFAULT_ROOM_ID)
        default_meta = None

        for room in rooms_data["rooms"]:
            if room["room_id"] == default_room:
                default_meta = room
                break

        if default_meta is None:
            raise RuntimeError("Default room not found")

        if default_meta["players_count"] < 2:
            return self.join_room(default_room)

        raise RuntimeError("Default room is full")

    def heartbeat(self):
        with self.lock:
            room_id = self.room_id

        if not room_id:
            return None

        r = requests.post(
            f"{self.base_url}/heartbeat",
            json={
                "room_id": room_id,
                "session_id": self.session_id,
                "client_type": self.client_type,
            },
            timeout=5,
        )
        r.raise_for_status()
        return r.json()

    def safe_leave(self):
        try:
            with self.lock:
                room_id = self.room_id
            if not room_id:
                return
            requests.post(
                f"{self.base_url}/leave",
                json={
                    "room_id": room_id,
                    "session_id": self.session_id,
                },
                timeout=2,
            )
        except Exception:
            pass

    def fetch_state(self):
        with self.lock:
            room_id = self.room_id
        if not room_id:
            return None

        r = requests.get(f"{self.base_url}/state/{room_id}", timeout=5)
        r.raise_for_status()
        data = r.json()
        with self.lock:
            self.state = data
        return data

    def make_move(self, position):
        with self.lock:
            room_id = self.room_id

        r = requests.post(
            f"{self.base_url}/move",
            json={
                "room_id": room_id,
                "session_id": self.session_id,
                "position": position,
            },
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()

        with self.lock:
            self.state = data
        return data

    def new_game(self):
        with self.lock:
            room_id = self.room_id

        r = requests.post(
            f"{self.base_url}/new_game",
            json={
                "room_id": room_id,
                "session_id": self.session_id,
            },
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()

        with self.lock:
            self.state = data
        return data

    def get_snapshot(self):
        with self.lock:
            return {
                "room_id": self.room_id,
                "player": self.player,
                "state": self.state.copy() if isinstance(self.state, dict) else self.state,
            }


class CliApp:
    def __init__(self, client):
        self.client = client
        self.running = True
        self.poll_thread = None
        self.last_render = ""

    def colorize_symbol(self, value):
        if value == "X":
            return "\033[31mX\033[0m"
        if value == "O":
            return "\033[34mO\033[0m"
        return value

    def render_board(self, board):
        def cell(i):
            value = board[i]
            return self.colorize_symbol(value) if value else str(i + 1)

        return "\n".join([
            f" {cell(0)} | {cell(1)} | {cell(2)} ",
            "---+---+---",
            f" {cell(3)} | {cell(4)} | {cell(5)} ",
            "---+---+---",
            f" {cell(6)} | {cell(7)} | {cell(8)} ",
        ])

    def print_rooms(self):
        data = self.client.list_rooms()
        print("\nAvailable rooms:")
        for room in data["rooms"]:
            if room["status"] == "finished":
                room_state = "FINISHED"
            elif room["ready"]:
                room_state = "READY"
            else:
                room_state = "WAITING"

            print(
                f"  {room['room_id']}"
                f" | {room['players_count']}/{room['capacity']}"
                f" | {room_state}"
                f" | clients: {', '.join(room['client_types']) if room['client_types'] else '-'}"
                f" | score X:{room['score']['X']} O:{room['score']['O']} D:{room['score']['draws']}"
            )

    def print_cli_instructions(self):
        print("")
        print("How to play in CLI mode:")
        print("  Type a single number from 1 to 9, then press Enter.")
        print("  Example: 5")
        print("")
        print("Board positions:")
        print("  1 | 2 | 3")
        print(" ---+---+---")
        print("  4 | 5 | 6")
        print(" ---+---+---")
        print("  7 | 8 | 9")
        print("")
        print("Other commands:")
        print("  newgame   start another round in the same room")
        print("  rooms     list available rooms")
        print("  refresh   refresh current state")
        print("  quit      leave the room and exit")
        print("")

    def render(self):
        snap = self.client.get_snapshot()
        room_id = snap["room_id"]
        player = snap["player"]
        state = snap["state"]

        if not state:
            return

        ready = state.get("ready", False)
        players_count = state.get("players_count", 0)
        winner = state["winner"]
        status = state["status"]

        lines = []
        lines.append("")
        lines.append("=" * 48)
        lines.append("TIC-TAC-TOE CLI")
        lines.append(f"Room:   {room_id}")
        lines.append(f"Player: {player}")
        lines.append(f"Players: {players_count}/2")
        lines.append(f"Ready:  {'YES' if ready else 'NO'}")
        lines.append(f"Status: {status}")
        lines.append(
            f"Score:  X={state['score']['X']}  O={state['score']['O']}  Draws={state['score']['draws']}"
        )
        lines.append("")
        lines.append(self.render_board(state["board"]))
        lines.append("")

        if not ready:
            lines.append("Waiting for second player...")
        elif winner == "draw":
            lines.append("Draw. Type 'newgame' to continue.")
        elif winner in ("X", "O"):
            lines.append(f"{winner} wins. Type 'newgame' to continue.")
        elif status == "playing":
            if state["turn"] == player:
                lines.append("Your turn to play.")
            else:
                lines.append("Waiting for opponent move.")
        elif status == "finished":
            lines.append("Game finished. Type 'newgame' to continue.")

        lines.append("")
        lines.append("Type a number 1-9 to place your piece.")
        lines.append("Commands: newgame, rooms, refresh, quit")
        lines.append("=" * 48)

        output = "\n".join(lines)
        if output != self.last_render:
            print(output)
            self.last_render = output

    def poll_loop(self):
        while self.running:
            try:
                self.client.heartbeat()
                self.client.fetch_state()
                self.render()
            except Exception:
                pass
            time.sleep(2)

    def setup_room(self):
        print("Tic-Tac-Toe")
        print("")
        print("1) Auto-join DEFAULT room")
        print("2) Create room")
        print("3) Join specific room")
        choice = (input("Choose [1/2/3] (default 1): ").strip() or "1")

        try:
            if choice == "1":
                data = self.client.auto_join_default()
            elif choice == "2":
                data = self.client.create_room()
            elif choice == "3":
                self.print_rooms()
                room_id = input("Enter room code: ").strip().upper()
                data = self.client.join_room(room_id)
            else:
                raise ValueError("Invalid choice")
        except Exception as e:
            raise RuntimeError(f"Setup failed: {friendly_error(e)}")

        print(f"\nJoined room: {data['room_id']}")
        print(f"You are player: {data['player']}")
        self.print_cli_instructions()
        self.client.fetch_state()
        self.render()

    def run(self):
        self.setup_room()
        self.poll_thread = threading.Thread(target=self.poll_loop, daemon=True)
        self.poll_thread.start()

        while True:
            cmd = input("\n> ").strip().lower()

            try:
                if cmd == "quit":
                    self.running = False
                    self.client.safe_leave()
                    break
                elif cmd == "refresh":
                    self.client.fetch_state()
                    self.render()
                elif cmd == "rooms":
                    self.print_rooms()
                elif cmd == "newgame":
                    self.client.new_game()
                    self.render()
                elif cmd.isdigit():
                    pos = int(cmd)
                    if pos < 1 or pos > 9:
                        print("Enter a number from 1 to 9.")
                        continue
                    self.client.make_move(pos - 1)
                    self.render()
                else:
                    print("Unknown command.")
                    print("Type a number 1-9 to play, or use: newgame, rooms, refresh, quit")
            except Exception as e:
                print(f"Error: {friendly_error(e)}")


class GuiApp:
    def __init__(self, client):
        self.client = client
        self.root = tk.Tk()
        self.root.title("TicTacToe Multiplayer")
        self.root.geometry("860x960")
        self.root.minsize(820, 920)

        self.player_text = tk.StringVar(value="-")
        self.status_text = tk.StringVar(value="Status: -")
        self.score_text = tk.StringVar(value="Score: X=0 O=0 Draws=0")
        self.ready_text = tk.StringVar(value="Waiting for second player...")
        self.message_text = tk.StringVar(value="Trying DEFAULT room...")
        self.room_selector_var = tk.StringVar()

        self.room_option_map = {}
        self.buttons = []
        self._suppress_room_change = False

        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        try:
            self.load_rooms()
            self.try_default_join()
        except Exception as e:
            self.message_text.set(f"Startup: {friendly_error(e)}")

        self.poll()

    def build_ui(self):
        self.root.configure(padx=18, pady=18)

        top = tk.Frame(self.root)
        top.pack(fill="x", pady=(0, 14))

        tk.Label(top, text="TicTacToe Multiplayer", font=("Arial", 22, "bold")).pack(pady=(0, 12))

        room_bar = tk.Frame(top)
        room_bar.pack(fill="x", pady=6)

        tk.Label(room_bar, text="Rooms:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 8))

        self.room_dropdown = ttk.Combobox(
            room_bar,
            textvariable=self.room_selector_var,
            state="readonly",
            width=78
        )
        self.room_dropdown.pack(side="left", padx=4)
        self.room_dropdown.bind("<<ComboboxSelected>>", self.on_room_selected)

        tk.Button(
            room_bar,
            text="Refresh Rooms",
            width=16,
            padx=8,
            command=self.load_rooms
        ).pack(side="left", padx=6)

        action_row = tk.Frame(top)
        action_row.pack(fill="x", pady=10)

        tk.Button(
            action_row,
            text="Create Room",
            width=20,
            height=2,
            font=("Arial", 12, "bold"),
            command=self.create_room
        ).pack(side="left", padx=6)

        tk.Button(
            action_row,
            text="New Game",
            width=20,
            height=2,
            font=("Arial", 12, "bold"),
            command=self.new_game
        ).pack(side="left", padx=6)

        info = tk.Frame(self.root, bd=1, relief="groove", padx=12, pady=12)
        info.pack(fill="x", pady=(0, 16))

        for var in [
            self.player_text,
            self.status_text,
            self.score_text
        ]:
            tk.Label(info, textvariable=var, anchor="w", font=("Arial", 12)).pack(fill="x", pady=2)

        self.ready_label = tk.Label(
            info,
            textvariable=self.ready_text,
            anchor="w",
            font=("Arial", 13, "bold"),
            fg="#b26a00"
        )
        self.ready_label.pack(fill="x", pady=(8, 2))

        board_outer = tk.Frame(self.root)
        board_outer.pack(pady=(0, 18))

        board_frame = tk.Frame(board_outer)
        board_frame.pack()

        for r in range(3):
            board_frame.grid_rowconfigure(r, minsize=180)
            board_frame.grid_columnconfigure(r, minsize=180)

        for r in range(3):
            for c in range(3):
                index = r * 3 + c
                btn = tk.Button(
                    board_frame,
                    text="",
                    width=5,
                    height=2,
                    font=("Arial", 42, "bold"),
                    bg="#f4f4f4",
                    activebackground="#e8e8e8",
                    command=lambda i=index: self.on_cell_click(i)
                )
                btn.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
                self.buttons.append(btn)

        bottom = tk.Frame(self.root, bd=1, relief="groove", padx=12, pady=12)
        bottom.pack(fill="x")

        tk.Label(
            bottom,
            textvariable=self.message_text,
            fg="#1f4fa3",
            wraplength=760,
            justify="left",
            anchor="w",
            font=("Arial", 12)
        ).pack(fill="x")

    def symbol_style(self, value):
        if value == "X":
            return {"fg": "#c62828"}
        if value == "O":
            return {"fg": "#1565c0"}
        return {"fg": "#222222"}

    def load_rooms(self):
        data = self.client.list_rooms()
        labels = []
        mapping = {}
        existing_selection = self.room_selector_var.get()
        selected_label = None

        for room in data["rooms"]:
            if room["status"] == "finished":
                room_state = "FINISHED"
            elif room["ready"]:
                room_state = "READY"
            else:
                room_state = "WAITING"

            label = (
                f"{room['room_id']} | {room['players_count']}/{room['capacity']} | "
                f"{room_state} | clients: {', '.join(room['client_types']) if room['client_types'] else '-'} | "
                f"score X:{room['score']['X']} O:{room['score']['O']} D:{room['score']['draws']}"
            )
            labels.append(label)
            mapping[label] = room["room_id"]

            if label == existing_selection:
                selected_label = label

        self.room_option_map = mapping
        self._suppress_room_change = True
        self.room_dropdown["values"] = labels

        if selected_label:
            self.room_selector_var.set(selected_label)
        elif labels:
            self.room_selector_var.set(labels[0])
        else:
            self.room_selector_var.set("")

        self.root.after(100, self._clear_room_change_suppression)

    def _clear_room_change_suppression(self):
        self._suppress_room_change = False

    def try_default_join(self):
        data = self.client.auto_join_default()
        self.client.fetch_state()
        self.message_text.set(f"Joined {data['room_id']} as {data['player']}.")
        self.refresh_ui()
        self.load_rooms()

    def selected_room_id(self):
        selected = self.room_selector_var.get()
        return self.room_option_map.get(selected, DEFAULT_ROOM_ID)

    def on_room_selected(self, _event=None):
        if self._suppress_room_change:
            return

        room_id = self.selected_room_id()
        if not room_id:
            return
        if room_id == self.client.room_id:
            return

        try:
            data = self.client.join_room(room_id)
            self.client.fetch_state()
            self.message_text.set(f"Joined {data['room_id']} as {data['player']}.")
            self.refresh_ui()
            self.load_rooms()
        except Exception as e:
            messagebox.showerror("Join Room Failed", friendly_error(e))

    def create_room(self):
        try:
            data = self.client.create_room()
            self.client.fetch_state()
            self.message_text.set(f"Created {data['room_id']}.")
            self.refresh_ui()
            self.load_rooms()
        except Exception as e:
            messagebox.showerror("Create Room Failed", friendly_error(e))

    def new_game(self):
        try:
            self.client.new_game()
            self.message_text.set("Started a new game.")
            self.refresh_ui()
        except Exception as e:
            messagebox.showerror("New Game Failed", friendly_error(e))

    def on_cell_click(self, index):
        snap = self.client.get_snapshot()
        state = snap["state"]
        player = snap["player"]

        if not state:
            return

        if state["status"] != "playing":
            self.message_text.set("Game is waiting for players or already finished.")
            return

        if state["winner"] is not None:
            self.message_text.set("Game finished. Press New Game.")
            return

        if state["turn"] != player:
            self.message_text.set("Not your turn.")
            return

        if state["board"][index] != "":
            self.message_text.set("Cell already taken.")
            return

        try:
            self.client.make_move(index)
            self.refresh_ui()
        except Exception as e:
            messagebox.showerror("Move Failed", friendly_error(e))

    def refresh_ui(self):
        snap = self.client.get_snapshot()
        player = snap["player"]
        state = snap["state"]

        self.player_text.set(player if player else "-")

        if not state:
            return

        self.status_text.set(f"Status: {state['status']}")
        self.score_text.set(
            f"Score: X={state['score']['X']}  O={state['score']['O']}  Draws={state['score']['draws']}"
        )

        ready = state.get("ready", False)
        status = state.get("status")
        winner = state.get("winner")

        if not ready:
            self.ready_text.set("Waiting for second player...")
            self.ready_label.config(fg="#b26a00")
        elif status == "finished":
            self.ready_text.set("Game finished. Press New Game to continue.")
            self.ready_label.config(fg="#7a1fa2")
        elif status == "playing":
            if state["turn"] == player:
                self.ready_text.set("Your turn to play.")
            else:
                self.ready_text.set("Waiting for opponent move.")
            self.ready_label.config(fg="#1b8a2f")
        else:
            self.ready_text.set("Room active.")
            self.ready_label.config(fg="#1b8a2f")

        enable_board = status == "playing" and winner is None and state["turn"] == player

        for i, btn in enumerate(self.buttons):
            value = state["board"][i] if state["board"][i] else ""
            style = self.symbol_style(value)
            btn.config(
                text=value,
                fg=style["fg"],
                state=("normal" if enable_board and state["board"][i] == "" else "disabled")
            )

        if not ready:
            self.message_text.set("Waiting for second player...")
        elif winner == "draw":
            self.message_text.set("Draw. Press New Game to continue.")
        elif winner in ("X", "O"):
            self.message_text.set(f"{winner} wins. Press New Game to continue.")
        elif status == "playing":
            if state["turn"] == player:
                self.message_text.set("Your turn to play.")
            else:
                self.message_text.set("Waiting for opponent move.")
        else:
            self.message_text.set("Room active.")

    def poll(self):
        try:
            if self.client.room_id:
                self.client.heartbeat()
                self.client.fetch_state()
                self.refresh_ui()
            self.load_rooms()
        except Exception:
            pass
        self.root.after(2000, self.poll)

    def on_close(self):
        self.client.safe_leave()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def print_startup_banner():
    print("")
    print("Tic-Tac-Toe Client")
    print("=" * 52)
    print("Defaults:")
    print(f"  mode   = {DEFAULT_MODE}")
    print(f"  server = {DEFAULT_SERVER_CHOICE} ({DEFAULT_BASE_URL})")
    print(f"  room   = {DEFAULT_ROOM_ID}")
    print("")
    print("Options:")
    print("  --mode gui|cli                 or -m gui|cli")
    print("  --server remote|local|URL      or -s remote|local|URL")
    print("")
    print("Server choices:")
    print(f"  remote -> {DEFAULT_REMOTE_URL}")
    print(f"  local  -> {DEFAULT_LOCAL_URL}")
    print("")
    print("Examples:")
    print("  python3 client.py")
    print("  python3 client.py --mode cli")
    print("  python3 client.py --server local")
    print("  python3 client.py --server remote")
    print("  python3 client.py --server http://192.168.1.50:8000")
    print("=" * 52)
    print("")

def resolve_server(server_value: str) -> str:
    value = server_value.strip().lower()

    if value == "remote":
        return DEFAULT_REMOTE_URL
    if value == "local":
        return DEFAULT_LOCAL_URL

    return server_value.rstrip("/")

def parse_args():
    parser = argparse.ArgumentParser(description="Tic-Tac-Toe multiplayer client")
    parser.add_argument(
        "-m", "--mode",
        choices=["cli", "gui"],
        default=DEFAULT_MODE,
        help=f"Client mode. Default: {DEFAULT_MODE}"
    )
    parser.add_argument(
        "-s", "--server",
        default=DEFAULT_SERVER_CHOICE,
        help="Server target: remote, local, or full URL. Default: remote"
    )
    return parser.parse_args()

def main():
    print_startup_banner()
    args = parse_args()

    client_type = "cli" if args.mode == "cli" else "gui"
    server_url = resolve_server(args.server)

    client = TicTacToeClient(server_url, client_type)

    try:
        if args.mode == "cli":
            CliApp(client).run()
        else:
            GuiApp(client).run()
    except KeyboardInterrupt:
        client.safe_leave()
        print("\nExiting.")

if __name__ == "__main__":
    main()