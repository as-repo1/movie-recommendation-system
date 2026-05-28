package com.reclens.data.repository

import android.content.Context
import android.content.SharedPreferences
import com.reclens.data.api.RetrofitClient
import com.reclens.data.api.WatchlistRequest
import com.reclens.data.api.WatchedRequest
import com.reclens.data.api.WatchedUpdate
import com.reclens.data.api.WatchedResponseEntry
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

class WatchlistRepository(private val context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("reclens_watchlist", Context.MODE_PRIVATE)
    private val gson = Gson()

    private fun getIds(): MutableSet<Int> {
        val json = prefs.getString("ids", "[]") ?: "[]"
        val type = object : TypeToken<MutableSet<Int>>() {}.type
        return gson.fromJson(json, type) ?: mutableSetOf()
    }

    private fun saveIds(ids: Set<Int>) {
        prefs.edit().putString("ids", gson.toJson(ids)).apply()
    }

    suspend fun syncWithBackend() {
        try {
            val api = RetrofitClient.getApi(context)
            val ids = api.getWatchlist().toSet()
            saveIds(ids)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    suspend fun addToWatchlist(movieId: Int) {
        // Optimistic local update
        val ids = getIds().also { it.add(movieId) }
        saveIds(ids)
        
        try {
            val api = RetrofitClient.getApi(context)
            val updated = api.addToWatchlist(WatchlistRequest(movieId)).toSet()
            saveIds(updated)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    suspend fun removeFromWatchlist(movieId: Int) {
        // Optimistic local update
        val ids = getIds().also { it.remove(movieId) }
        saveIds(ids)

        try {
            val api = RetrofitClient.getApi(context)
            val updated = api.removeFromWatchlist(movieId).toSet()
            saveIds(updated)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun getWatchlist(): Set<Int> = getIds()
    fun isInWatchlist(movieId: Int) = getIds().contains(movieId)
}

data class WatchedEntry(val rating: Float, val addedAt: Long = System.currentTimeMillis())

class WatchedRepository(private val context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("reclens_watched", Context.MODE_PRIVATE)
    private val gson = Gson()
    private val type = object : TypeToken<MutableMap<Int, WatchedEntry>>() {}.type

    private fun getMap(): MutableMap<Int, WatchedEntry> {
        val json = prefs.getString("map", "{}") ?: "{}"
        return gson.fromJson(json, type) ?: mutableMapOf()
    }

    private fun saveMap(map: Map<Int, WatchedEntry>) {
        prefs.edit().putString("map", gson.toJson(map)).apply()
    }

    suspend fun syncWithBackend() {
        try {
            val api = RetrofitClient.getApi(context)
            val backendMap = api.getWatched()
            val localMap = mutableMapOf<Int, WatchedEntry>()
            backendMap.forEach { (movieIdStr, entry) ->
                val movieId = movieIdStr.toIntOrNull()
                if (movieId != null) {
                    localMap[movieId] = WatchedEntry(entry.rating)
                }
            }
            saveMap(localMap)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    suspend fun markWatched(movieId: Int, rating: Float) {
        // Optimistic local update
        val map = getMap().also { it[movieId] = WatchedEntry(rating) }
        saveMap(map)

        try {
            val api = RetrofitClient.getApi(context)
            val responseMap = api.markWatched(WatchedRequest(movieId, rating))
            updateLocalMapFromResponse(responseMap)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    suspend fun updateRating(movieId: Int, rating: Float) {
        // Optimistic local update
        val map = getMap().also { it[movieId] = WatchedEntry(rating) }
        saveMap(map)

        try {
            val api = RetrofitClient.getApi(context)
            val responseMap = api.updateRating(movieId, WatchedUpdate(rating))
            updateLocalMapFromResponse(responseMap)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    suspend fun removeWatched(movieId: Int) {
        // Optimistic local update
        val map = getMap().also { it.remove(movieId) }
        saveMap(map)

        try {
            val api = RetrofitClient.getApi(context)
            val responseMap = api.removeWatched(movieId)
            updateLocalMapFromResponse(responseMap)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun updateLocalMapFromResponse(responseMap: Map<String, WatchedResponseEntry>) {
        val localMap = mutableMapOf<Int, WatchedEntry>()
        responseMap.forEach { (movieIdStr, entry) ->
            val movieId = movieIdStr.toIntOrNull()
            if (movieId != null) {
                localMap[movieId] = WatchedEntry(entry.rating)
            }
        }
        saveMap(localMap)
    }

    fun getWatched(): Map<Int, WatchedEntry> = getMap()
    fun isWatched(movieId: Int) = getMap().containsKey(movieId)
    fun getRating(movieId: Int) = getMap()[movieId]?.rating

    fun getRatedMovies() = getMap().entries.map { (id, entry) ->
        mapOf("movieId" to id, "rating" to entry.rating)
    }
}
