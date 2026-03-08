package com.example.tictactoemultiplayer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

data class UiState(
    val roomId: String = "",
    val player: String = "",
    val board: List<String> = List(9) { "" },
    val status: String = "not connected",
    val ready: Boolean = false,
    val turn: String = "",
    val winner: String? = null,
    val scoreX: Int = 0,
    val scoreO: Int = 0,
    val scoreDraws: Int = 0,
    val rooms: List<RoomInfo> = emptyList(),
    val selectedRoomId: String = "DEFAULT",
    val message: String = "Connecting...",
    val isLoading: Boolean = false
)

class GameViewModel : ViewModel() {
    private val api = ApiClient.api
    private val sessionId = UUID.randomUUID().toString()
    private val clientType = "android"

    var uiState = androidx.compose.runtime.mutableStateOf(UiState())
        private set

    private var pollingJob: Job? = null

    init {
        loadRoomsAndAutoJoin()
    }

    private fun setMessage(msg: String) {
        uiState.value = uiState.value.copy(message = msg)
    }

    private fun mapState(state: GameState, message: String? = null) {
        uiState.value = uiState.value.copy(
            roomId = state.room_id,
            board = state.board,
            status = state.status,
            ready = state.ready,
            turn = state.turn,
            winner = state.winner,
            scoreX = state.score.X,
            scoreO = state.score.O,
            scoreDraws = state.score.draws,
            selectedRoomId = state.room_id,
            message = message ?: uiState.value.message
        )
    }

    fun loadRooms() {
        viewModelScope.launch {
            try {
                val rooms = api.listRooms()
                uiState.value = uiState.value.copy(
                    rooms = rooms.rooms,
                    selectedRoomId = uiState.value.selectedRoomId.ifBlank { rooms.default_room }
                )
            } catch (e: Exception) {
                setMessage("Failed to load rooms: ${friendlyError(e)}")
            }
        }
    }

    fun loadRoomsAndAutoJoin() {
        viewModelScope.launch {
            try {
                val roomsResponse = api.listRooms()
                val defaultRoom = roomsResponse.rooms.firstOrNull { it.room_id == roomsResponse.default_room }

                uiState.value = uiState.value.copy(
                    rooms = roomsResponse.rooms,
                    selectedRoomId = roomsResponse.default_room,
                    isLoading = true
                )

                if (defaultRoom != null && defaultRoom.players_count < 2) {
                    val joined = api.joinRoom(
                        JoinRoomRequest(
                            room_id = roomsResponse.default_room,
                            session_id = sessionId,
                            client_type = clientType
                        )
                    )
                    uiState.value = uiState.value.copy(player = joined.player, roomId = joined.room_id)
                    loadState("Joined ${joined.room_id} as ${joined.player}")
                    startPolling()
                } else {
                    setMessage("Default room is full. Select another room.")
                }
            } catch (e: Exception) {
                uiState.value = uiState.value.copy(isLoading = false)
                setMessage("Startup failed: ${friendlyError(e)}")
            }
        }
    }

    fun createRoom() {
        viewModelScope.launch {
            try {
                val response = api.createRoom(
                    CreateRoomRequest(
                        session_id = sessionId,
                        client_type = clientType
                    )
                )
                uiState.value = uiState.value.copy(
                    roomId = response.room_id,
                    player = response.player,
                    selectedRoomId = response.room_id
                )
                loadRooms()
                loadState("Created ${response.room_id} as ${response.player}")
                startPolling()
            } catch (e: Exception) {
                setMessage("Create room failed: ${friendlyError(e)}")
            }
        }
    }

    fun joinSelectedRoom() {
        val roomId = uiState.value.selectedRoomId
        if (roomId.isBlank()) {
            setMessage("No room selected")
            return
        }

        viewModelScope.launch {
            try {
                val response = api.joinRoom(
                    JoinRoomRequest(
                        room_id = roomId,
                        session_id = sessionId,
                        client_type = clientType
                    )
                )
                uiState.value = uiState.value.copy(
                    roomId = response.room_id,
                    player = response.player
                )
                loadRooms()
                loadState("Joined ${response.room_id} as ${response.player}")
                startPolling()
            } catch (e: Exception) {
                setMessage("Join room failed: ${friendlyError(e)}")
            }
        }
    }

    fun selectRoom(roomId: String) {
        uiState.value = uiState.value.copy(selectedRoomId = roomId)
    }

    fun loadState(message: String? = null) {
        val roomId = uiState.value.roomId
        if (roomId.isBlank()) return

        viewModelScope.launch {
            try {
                val state = api.getState(roomId)
                uiState.value = uiState.value.copy(isLoading = false)
                mapState(state, message)
            } catch (e: Exception) {
                uiState.value = uiState.value.copy(isLoading = false)
                setMessage("Load state failed: ${friendlyError(e)}")
            }
        }
    }

    fun makeMove(index: Int) {
        val state = uiState.value
        if (state.roomId.isBlank()) {
            setMessage("Join a room first")
            return
        }

        viewModelScope.launch {
            try {
                val newState = api.move(
                    MoveRequest(
                        room_id = state.roomId,
                        session_id = sessionId,
                        position = index
                    )
                )
                mapState(newState)
            } catch (e: Exception) {
                setMessage("Move failed: ${friendlyError(e)}")
            }
        }
    }

    fun newGame() {
        val roomId = uiState.value.roomId
        if (roomId.isBlank()) {
            setMessage("Join a room first")
            return
        }

        viewModelScope.launch {
            try {
                val state = api.newGame(
                    NewGameRequest(
                        room_id = roomId,
                        session_id = sessionId
                    )
                )
                mapState(state, "Started a new game")
            } catch (e: Exception) {
                setMessage("New game failed: ${friendlyError(e)}")
            }
        }
    }

    private fun heartbeat() {
        val roomId = uiState.value.roomId
        if (roomId.isBlank()) return

        viewModelScope.launch {
            try {
                api.heartbeat(
                    HeartbeatRequest(
                        room_id = roomId,
                        session_id = sessionId,
                        client_type = clientType
                    )
                )
            } catch (_: Exception) {
            }
        }
    }

    private fun startPolling() {
        if (pollingJob != null) return

        pollingJob = viewModelScope.launch {
            while (true) {
                try {
                    heartbeat()
                    loadRooms()
                    loadState()
                } catch (_: Exception) {
                }
                delay(2000)
            }
        }
    }

    private fun friendlyError(e: Exception): String {
        val text = e.message ?: return "Unknown error"
        return when {
            "HTTP 422" in text -> "Server rejected the request format"
            "HTTP 400" in text -> "Room is full or request is invalid"
            "HTTP 404" in text -> "Room not found"
            else -> text
        }
    }
}
