package com.example.tictactoemultiplayer

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val vm = GameViewModel()

        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    GameScreen(vm)
                }
            }
        }
    }
}

@Composable
fun GameScreen(vm: GameViewModel) {
    val state by vm.uiState
    var roomsExpanded by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text("TicTacToe Multiplayer", style = MaterialTheme.typography.headlineSmall)
        Spacer(modifier = Modifier.height(12.dp))

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { vm.createRoom() }) {
                Text("Create Room")
            }

            OutlinedButton(onClick = { vm.newGame() }) {
                Text("New Game")
            }

            OutlinedButton(
                onClick = { vm.loadRooms() },
                modifier = Modifier.height(40.dp)
            ) {
                Text("Refresh")
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        Text("Player: ${state.player.ifBlank { "-" }}")

        val gameMessage = when {
            state.winner == "X" -> "Game finished — Winner: X"
            state.winner == "O" -> "Game finished — Winner: O"
            state.winner == "Draw" -> "Game finished — Draw"
            state.status == "playing" && state.turn == state.player -> "Your turn"
            state.status == "playing" -> "Waiting for opponent move"
            state.status == "waiting" -> "Waiting for second player"
            else -> state.status
        }

Text(gameMessage, fontWeight = FontWeight.Bold)

Text("Score: X=${state.scoreX}  O=${state.scoreO}  Draws=${state.scoreDraws}")
Text(state.message)

        Spacer(modifier = Modifier.height(12.dp))

        Text("Rooms", style = MaterialTheme.typography.titleMedium)
        Spacer(modifier = Modifier.height(8.dp))

        Box(modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(
                onClick = { roomsExpanded = true },
                modifier = Modifier.fillMaxWidth()
            ) {
                val selectedRoom = state.rooms.firstOrNull { it.room_id == state.selectedRoomId }
                val roomLabel = if (selectedRoom != null) {
                    "${selectedRoom.room_id}  ${selectedRoom.players_count}/${selectedRoom.capacity}"
                } else {
                    state.selectedRoomId.ifBlank { "Select room" }
                }
                Text(roomLabel)
            }

            DropdownMenu(
                expanded = roomsExpanded,
                onDismissRequest = { roomsExpanded = false },
                modifier = Modifier.fillMaxWidth(0.95f)
            ) {
                state.rooms.forEach { room ->
                    val clientText = if (room.client_types.isEmpty()) "-" else room.client_types.joinToString(", ")
                    DropdownMenuItem(
                        text = {
                            Column {
                                Text(
                                    "${room.room_id}  ${room.players_count}/${room.capacity}",
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    "status: ${room.status}   clients: $clientText",
                                    style = MaterialTheme.typography.bodySmall
                                )
                            }
                        },
                        onClick = {
                            roomsExpanded = false
                            vm.selectRoom(room.room_id)
                            vm.joinSelectedRoom()
                        }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Board(
            board = state.board,
            enabled = state.status == "playing" && state.winner == null && state.turn == state.player,
            onCellClick = { vm.makeMove(it) }
        )
    }
}

@Composable
fun Board(
    board: List<String>,
    enabled: Boolean,
    onCellClick: (Int) -> Unit
) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(3),
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        userScrollEnabled = false
    ) {
        itemsIndexed(board.take(9)) { index, value ->
            val color = when (value) {
                "X" -> Color.Red
                "O" -> Color.Blue
                else -> Color.Black
            }

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f)
                    .clickable(enabled = enabled && value.isEmpty()) { onCellClick(index) },
                border = BorderStroke(1.dp, Color.Gray)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.White),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = value,
                        color = color,
                        style = MaterialTheme.typography.headlineLarge
                    )
                }
            }
        }
    }
}
