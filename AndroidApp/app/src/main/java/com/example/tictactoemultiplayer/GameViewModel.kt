package com.example.tictactoemultiplayer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

data class UiState(
    val roomId: String = "",
    val player: String = "",
    val board: List<String> = List(9) { "" },
    val turn: String = "X",
    val winner: String? = null,
    val status: String = "idle",
    val message: String = "",
    val joinRoomInput: String = "",
    val isLoading: Boolean = false
)

class GameViewModel : ViewModel() {

    var uiState = androidx.compose.runtime.mutableStateOf(UiState())
        private set

    private var pollJob: Job? = null

    fun onJoinRoomInputChanged(value: String) {
        uiState.value = uiState.value.copy(joinRoomInput = value.uppercase())
    }

    fun createRoom() {
        viewModelScope.launch {
            uiState.value = uiState.value.copy(isLoading = true, message = "")
            try {
                val response = ApiClient.api.createRoom()
                uiState.value = uiState.value.copy(
                    roomId = response.room_id,
                    player = response.player,
                    board = List(9) { "" },
                    turn = "X",
                    winner = null,
                    status = "waiting",
                    message = "Room created. Share code: ${response.room_id}",
                    isLoading = false
                )
                startPolling()
            } catch (e: Exception) {
                uiState.value = uiState.value.copy(
                    isLoading = false,
                    message = "Create room failed: ${e.message}"
                )
            }
        }
    }

    fun joinRoom() {
        val room = uiState.value.joinRoomInput.trim().uppercase()
        if (room.isBlank()) {
            uiState.value = uiState.value.copy(message = "Enter room code")
            return
        }

        viewModelScope.launch {
            uiState.value = uiState.value.copy(isLoading = true, message = "")
            try {
                val response = ApiClient.api.joinRoom(JoinRoomRequest(room))
                val state = ApiClient.api.getState(response.room_id)
                uiState.value = uiState.value.copy(
                    roomId = response.room_id,
                    player = response.player,
                    board = state.board,
                    turn = state.turn,
                    winner = state.winner,
                    status = state.status,
                    message = "Joined room ${response.room_id}",
                    isLoading = false
                )
                startPolling()
            } catch (e: Exception) {
                uiState.value = uiState.value.copy(
                    isLoading = false,
                    message = "Join room failed: ${e.message}"
                )
            }
        }
    }

    fun loadState() {
        val roomId = uiState.value.roomId
        if (roomId.isBlank()) return

        viewModelScope.launch {
            try {
                val state = ApiClient.api.getState(roomId)
                uiState.value = uiState.value.copy(
                    board = state.board,
                    turn = state.turn,
                    winner = state.winner,
                    status = state.status
                )
            } catch (e: Exception) {
                uiState.value = uiState.value.copy(message = "Load state failed: ${e.message}")
            }
        }
    }

    fun makeMove(position: Int) {
        val state = uiState.value

        if (state.roomId.isBlank()) return
        if (state.player.isBlank()) return
        if (state.status != "playing") return
        if (state.winner != null) return
        if (state.turn != state.player) {
            uiState.value = state.copy(message = "Not your turn")
            return
        }
        if (state.board[position].isNotEmpty()) return

        viewModelScope.launch {
            try {
                val updated = ApiClient.api.makeMove(
                    MoveRequest(
                        room_id = state.roomId,
                        player = state.player,
                        position = position
                    )
                )
                uiState.value = uiState.value.copy(
                    board = updated.board,
                    turn = updated.turn,
                    winner = updated.winner,
                    status = updated.status,
                    message = ""
                )
            } catch (e: Exception) {
                uiState.value = uiState.value.copy(message = "Move failed: ${e.message}")
            }
        }
    }

    fun resetGame() {
        val roomId = uiState.value.roomId
        if (roomId.isBlank()) return

        viewModelScope.launch {
            try {
                val updated = ApiClient.api.reset(ResetRequest(roomId))
                uiState.value = uiState.value.copy(
                    board = updated.board,
                    turn = updated.turn,
                    winner = updated.winner,
                    status = updated.status,
                    message = "Game reset"
                )
            } catch (e: Exception) {
                uiState.value = uiState.value.copy(message = "Reset failed: ${e.message}")
            }
        }
    }

    private fun startPolling() {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (true) {
                val roomId = uiState.value.roomId
                if (roomId.isNotBlank()) {
                    try {
                        val state = ApiClient.api.getState(roomId)
                        uiState.value = uiState.value.copy(
                            board = state.board,
                            turn = state.turn,
                            winner = state.winner,
                            status = state.status
                        )
                    } catch (_: Exception) {
                    }
                }
                delay(1000)
            }
        }
    }

    override fun onCleared() {
        pollJob?.cancel()
        super.onCleared()
    }
}
