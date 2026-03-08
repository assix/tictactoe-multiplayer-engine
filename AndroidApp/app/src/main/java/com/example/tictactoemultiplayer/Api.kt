package com.example.tictactoemultiplayer

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

data class CreateRoomRequest(
    val session_id: String,
    val client_type: String
)

data class JoinRoomRequest(
    val room_id: String,
    val session_id: String,
    val client_type: String
)

data class MoveRequest(
    val room_id: String,
    val session_id: String,
    val position: Int
)

data class NewGameRequest(
    val room_id: String,
    val session_id: String
)

data class HeartbeatRequest(
    val room_id: String,
    val session_id: String,
    val client_type: String
)

data class RoomJoinResponse(
    val room_id: String,
    val player: String
)

data class Players(
    val X: String? = null,
    val O: String? = null
)

data class Score(
    val X: Int = 0,
    val O: Int = 0,
    val draws: Int = 0
)

data class GameState(
    val room_id: String,
    val board: List<String>,
    val players: Players,
    val turn: String,
    val winner: String?,
    val status: String,
    val score: Score,
    val players_count: Int = 0,
    val ready: Boolean = false,
    val client_types: List<String> = emptyList()
)

data class RoomInfo(
    val room_id: String,
    val is_default: Boolean = false,
    val players_count: Int = 0,
    val capacity: Int = 2,
    val status: String = "waiting",
    val ready: Boolean = false,
    val turn: String? = null,
    val winner: String? = null,
    val client_types: List<String> = emptyList(),
    val score: Score = Score()
)

data class RoomsResponse(
    val default_room: String,
    val rooms: List<RoomInfo>
)

interface ApiService {
    @GET("/")
    suspend fun root(): Map<String, Any>

    @GET("/rooms")
    suspend fun listRooms(): RoomsResponse

    @POST("/create_room")
    suspend fun createRoom(@Body request: CreateRoomRequest): RoomJoinResponse

    @POST("/join_room")
    suspend fun joinRoom(@Body request: JoinRoomRequest): RoomJoinResponse

    @POST("/move")
    suspend fun move(@Body request: MoveRequest): GameState

    @POST("/new_game")
    suspend fun newGame(@Body request: NewGameRequest): GameState

    @POST("/heartbeat")
    suspend fun heartbeat(@Body request: HeartbeatRequest): Map<String, Any>

    @GET("/state/{roomId}")
    suspend fun getState(@Path("roomId") roomId: String): GameState
}

object ApiClient {
    private val retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val api: ApiService by lazy {
        retrofit.create(ApiService::class.java)
    }
}
