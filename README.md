# TicTacToe Multiplayer Engine

A room-based multiplayer Tic-Tac-Toe project built with a Python FastAPI server and multiple clients:

- Linux CLI client
- Linux Tkinter GUI client
- Android client

This repository demonstrates a simple client-server multiplayer architecture with room-based gameplay, score tracking, room management, and cross-platform clients.

## Features

- FastAPI multiplayer game server
- Room-based matchmaking
- Default room plus custom rooms
- CLI client for terminal gameplay
- GUI client for Linux desktop gameplay
- Android client
- Score tracking across rounds
- New Game without leaving the room
- Automatic room cleanup when players disconnect
- Local or cloud-hosted deployment

## Project Structure

```text
tictactoe-multiplayer-engine/
├── AndroidApp/
├── client.py
├── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Requirements

- Python 3.10+
- pip
- Tkinter for GUI mode on Linux
- Java 17 for Android builds
- Android SDK command-line tools or Android Studio for Android builds

## Python Setup

Clone the repository:

```bash
git clone https://github.com/assix/tictactoe-multiplayer-engine.git
cd tictactoe-multiplayer-engine
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

On Ubuntu, install Tkinter if needed:

```bash
sudo apt update
sudo apt install python3-tk
```

## Run the Server Locally

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --no-access-log
```

The server automatically creates the `DEFAULT` room on startup.

## Run the Python Client

### GUI mode

```bash
python3 client.py
```

or

```bash
python3 client.py --mode gui
```

### CLI mode

```bash
python3 client.py --mode cli
```

## Server Selection

The Python client defaults to the hosted server:

```text
https://tictactoe-multiplayer-engine.onrender.com
```

Use the local server:

```bash
python3 client.py --server local
```

Use the hosted server explicitly:

```bash
python3 client.py --server remote
```

Use any custom server URL:

```bash
python3 client.py --server http://192.168.1.50:8000
```

## CLI Gameplay

When the CLI starts, press Enter to auto-join the default room.

Board layout:

```text
 1 | 2 | 3
---+---+---
 4 | 5 | 6
---+---+---
 7 | 8 | 9
```

Example move:

```text
> 5
```

Other commands:

```text
newgame
rooms
refresh
quit
```

## Android App

The Android client is located in:

```text
AndroidApp/
```

It supports:

- auto-joining the `DEFAULT` room if space is available
- creating a room
- selecting available rooms from a dropdown
- playing and starting a new game
- connecting to the hosted Render server

## Build the Android APK

Make sure Java 17 and the Android SDK are installed, then from the Android project root:

```bash
cd AndroidApp
./gradlew assembleDebug
```

The APK will be generated at:

```text
AndroidApp/app/build/outputs/apk/debug/app-debug.apk
```

## Hosted Server

Public server URL:

```text
https://tictactoe-multiplayer-engine.onrender.com
```

Python client example:

```bash
python3 client.py --server remote
```

## Deploy the Server on Render

This project can be deployed as a Python web service on Render.

Recommended build command:

```bash
pip install -r requirements.txt
```

Recommended start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT --no-access-log
```

## Suggested GitHub Topics

```text
tictactoe
multiplayer
fastapi
python
game-server
client-server
tkinter
cli
android
render
```

## Future Improvements

- WebSocket-based real-time updates
- Persistent room and score storage
- User accounts
- Spectator mode
- Browser client
- Automated APK builds with GitHub Actions

## License

MIT License
