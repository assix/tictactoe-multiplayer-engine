package com.example.tictactoemultiplayer

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    GameScreen()
                }
            }
        }
    }
}

@Composable
fun GameScreen(vm: GameViewModel = viewModel()) {
    val state = vm.uiState.value

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "Tic-Tac-Toe Multiplayer",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )

        Card {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = { vm.createRoom() },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Create Room")
                }

                OutlinedTextField(
                    value = state.joinRoomInput,
                    onValueChange = vm::onJoinRoomInputChanged,
                    label = { Text("Room code") },
                    modifier = Modifier.fillMaxWidth()
                )

                Button(
                    onClick = { vm.joinRoom() },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Join Room")
                }
            }
        }

        if (state.roomId.isNotBlank()) {
            Card {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text("Room: ${state.roomId}", fontWeight = FontWeight.Bold)
                    Text("You are: ${state.player}")
                    Text("Status: ${state.status}")
                    Text("Turn: ${state.turn}")
                    Text(
                        "Winner: ${
                            when (state.winner) {
                                null -> "-"
                                "draw" -> "Draw"
                                else -> state.winner
                            }
                        }"
                    )

                    Button(
                        onClick = { vm.resetGame() },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Reset Game")
                    }
                }
            }

            Board(
                board = state.board,
                enabled = state.status == "playing" && state.turn == state.player && state.winner == null,
                onCellClick = vm::makeMove
            )
        }

        if (state.message.isNotBlank()) {
            Text(
                text = state.message,
                color = MaterialTheme.colorScheme.primary
            )
        }

        if (state.isLoading) {
            CircularProgressIndicator()
        }
    }
}

@Composable
fun Board(
    board: List<String>,
    enabled: Boolean,
    onCellClick: (Int) -> Unit
) {
    Column(
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        for (row in 0..2) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                for (col in 0..2) {
                    val index = row * 3 + col
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .aspectRatio(1f)
                            .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(12.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(12.dp))
                            .clickable(enabled = enabled && board[index].isEmpty()) {
                                onCellClick(index)
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = board[index],
                            style = MaterialTheme.typography.displayMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}
