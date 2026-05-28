package com.cinematch.data.repository

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

class WatchlistRepository(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("cinematch_watchlist", Context.MODE_PRIVATE)
    private val gson = Gson()

    private fun getIds(): MutableSet<Int> {
        val json = prefs.getString("ids", "[]") ?: "[]"
        val type = object : TypeToken<MutableSet<Int>>() {}.type
        return gson.fromJson(json, type) ?: mutableSetOf()
    }

    private fun saveIds(ids: Set<Int>) {
        prefs.edit().putString("ids", gson.toJson(ids)).apply()
    }

    fun addToWatchlist(movieId: Int) = saveIds(getIds().also { it.add(movieId) })
    fun removeFromWatchlist(movieId: Int) = saveIds(getIds().also { it.remove(movieId) })
    fun getWatchlist(): Set<Int> = getIds()
    fun isInWatchlist(movieId: Int) = getIds().contains(movieId)
}

data class WatchedEntry(val rating: Float, val addedAt: Long = System.currentTimeMillis())

class WatchedRepository(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("cinematch_watched", Context.MODE_PRIVATE)
    private val gson = Gson()
    private val type = object : TypeToken<MutableMap<Int, WatchedEntry>>() {}.type

    private fun getMap(): MutableMap<Int, WatchedEntry> {
        val json = prefs.getString("map", "{}") ?: "{}"
        return gson.fromJson(json, type) ?: mutableMapOf()
    }

    private fun saveMap(map: Map<Int, WatchedEntry>) {
        prefs.edit().putString("map", gson.toJson(map)).apply()
    }

    fun markWatched(movieId: Int, rating: Float) =
        saveMap(getMap().also { it[movieId] = WatchedEntry(rating) })

    fun removeWatched(movieId: Int) = saveMap(getMap().also { it.remove(movieId) })
    fun getWatched(): Map<Int, WatchedEntry> = getMap()
    fun isWatched(movieId: Int) = getMap().containsKey(movieId)
    fun getRating(movieId: Int) = getMap()[movieId]?.rating

    fun getRatedMovies() = getMap().entries.map { (id, entry) ->
        mapOf("movieId" to id, "rating" to entry.rating)
    }
}
