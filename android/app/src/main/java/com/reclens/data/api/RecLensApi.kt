package com.reclens.data.api

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

// ── Data models ──────────────────────────────────────────────────────────────

data class Movie(
    val id: Int = 0,
    val title: String = "",
    val overview: String = "",
    @SerializedName("poster_url")    val posterUrl: String = "",
    @SerializedName("backdrop_url")  val backdropUrl: String = "",
    val genres: List<String> = emptyList(),
    val year: Int? = null,
    @SerializedName("vote_average")  val voteAverage: Double = 0.0,
    @SerializedName("vote_count")    val voteCount: Int = 0,
    val runtime: Int? = null,
    @SerializedName("imdb_id")       val imdbId: String = "",
    val director: String = "",
    val writer: String = "",
    val cast: List<String> = emptyList()
)

data class SearchResponse(
    val movies: List<Movie> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val query: String = ""
)

data class SimilarResponse(
    @SerializedName("source_movie")  val sourceMovie: Movie = Movie(),
    val recommendations: List<Movie> = emptyList(),
    val engine: String = ""
)

data class RatedMovie(
    @SerializedName("movie_id") val movieId: Int,
    val rating: Float
)

data class PersonalisedRequest(
    val ratings: List<RatedMovie>,
    val n: Int = 10
)

data class PersonalisedResponse(
    val recommendations: List<Movie> = emptyList(),
    val engine: String = ""
)

// ── Auth models ──────────────────────────────────────────────────────────────

data class AuthRequest(
    val username: String,
    val password: String,
    @SerializedName("anonymous_session_id") val anonymousSessionId: String? = null
)

data class AuthUser(
    val id: Int,
    val username: String,
    @SerializedName("created_at") val createdAt: String
)

data class AuthResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    val user: AuthUser
)

// ── List models ──────────────────────────────────────────────────────────────

data class WatchlistRequest(
    @SerializedName("movie_id") val movieId: Int
)

data class WatchedRequest(
    @SerializedName("movie_id") val movieId: Int,
    val rating: Float
)

data class WatchedUpdate(
    val rating: Float
)

data class WatchedResponseEntry(
    val rating: Float,
    val addedAt: String
)

data class HealthResponse(
    val status: String = "",
    @SerializedName("content_model") val contentModel: Boolean = false,
    @SerializedName("lightfm_model") val lightfmModel: Boolean = false
)

// ── Retrofit interface ────────────────────────────────────────────────────────

interface RecLensApi {

    // Movies
    @GET("api/movies/popular")
    suspend fun getPopular(@Query("page") page: Int = 1): List<Movie>

    @GET("api/movies/search")
    suspend fun search(
        @Query("q")    query: String,
        @Query("page") page: Int = 1
    ): SearchResponse

    @GET("api/movies/{id}")
    suspend fun getMovie(@Path("id") id: Int): Movie

    @GET("api/recommendations/similar/{id}")
    suspend fun getSimilar(
        @Path("id") id: Int,
        @Query("n") n: Int = 8
    ): SimilarResponse

    @POST("api/recommendations/personalised")
    suspend fun getPersonalised(@Body body: PersonalisedRequest): PersonalisedResponse

    // Watchlist
    @GET("api/watchlist")
    suspend fun getWatchlist(): List<Int>

    @POST("api/watchlist")
    suspend fun addToWatchlist(@Body body: WatchlistRequest): List<Int>

    @DELETE("api/watchlist/{id}")
    suspend fun removeFromWatchlist(@Path("id") id: Int): List<Int>

    // Watched
    @GET("api/watched")
    suspend fun getWatched(): Map<String, WatchedResponseEntry>

    @POST("api/watched")
    suspend fun markWatched(@Body body: WatchedRequest): Map<String, WatchedResponseEntry>

    @PUT("api/watched/{id}")
    suspend fun updateRating(@Path("id") id: Int, @Body body: WatchedUpdate): Map<String, WatchedResponseEntry>

    @DELETE("api/watched/{id}")
    suspend fun removeWatched(@Path("id") id: Int): Map<String, WatchedResponseEntry>

    // Authentication
    @POST("api/auth/register")
    suspend fun register(@Body body: AuthRequest): AuthResponse

    @POST("api/auth/login")
    suspend fun login(@Body body: AuthRequest): AuthResponse

    @GET("api/auth/me")
    suspend fun getMe(): AuthUser

    // System
    @GET("health")
    suspend fun checkHealth(): HealthResponse
}
