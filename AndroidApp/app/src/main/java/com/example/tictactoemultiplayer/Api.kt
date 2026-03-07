package com.example.tictactoemultiplayer

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

data class CreateRoomResponse(
    val room_id: String,
    val player: String
)

data class JoinRoomRequest(
    val room_id: String
)

data class JoinRoomResponse(
    val room_id: String,
    val player: String
)

data class MoveRequest(
    val room_id: String,
    val player: String,
    val position: Int
)

data class ResetRequest(
    val room_id: String
)

data class Players(
    val X: String?,
    val O: String?
)

data class GameState(
    val board: List<String>,
    val players: Players,
    val turn: String,
    val winner: String?,
    val status: String
)

interface ApiService {
    @POST("create_room")
    suspend fun createRoom(): CreateRoomResponse

    @POST("join_room")
    suspend fun joinRoom(@Body body: JoinRoomRequest): JoinRoomResponse

    @GET("state/{roomId}")
    suspend fun getState(@Path("roomId") roomId: String): GameState

    @POST("move")
    suspend fun makeMove(@Body body: MoveRequest): GameState

    @POST("reset")
    suspend fun reset(@Body body: ResetRequest): GameState
}

object ApiClient {
    val api: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
