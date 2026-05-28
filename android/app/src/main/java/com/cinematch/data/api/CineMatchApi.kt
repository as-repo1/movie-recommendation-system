package com.cinematch.data.api

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
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
    @SerializedName("imdb_id")       val imdbId: String = ""
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

// ── Retrofit interface ────────────────────────────────────────────────────────

interface CineMatchApi {

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
}
