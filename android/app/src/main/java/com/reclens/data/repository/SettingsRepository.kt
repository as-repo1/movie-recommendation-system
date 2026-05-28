package com.reclens.data.repository

import android.content.Context
import android.content.SharedPreferences
import com.reclens.BuildConfig
import java.util.UUID

class SettingsRepository(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("reclens_settings", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_BASE_URL = "base_url"
        private const val KEY_SESSION_ID = "session_id"
        private const val KEY_AUTH_TOKEN = "auth_token"
        private const val KEY_USERNAME = "username"
        private const val KEY_REC_COUNT = "rec_count"
        private const val KEY_THEME_ACCENT = "theme_accent"
    }

    init {
        // Automatically generate a session UUID if none exists
        if (getSessionId().isBlank()) {
            val uuid = UUID.randomUUID().toString()
            prefs.edit().putString(KEY_SESSION_ID, uuid).apply()
        }
    }

    fun getBaseUrl(): String {
        return prefs.getString(KEY_BASE_URL, BuildConfig.API_BASE_URL) ?: BuildConfig.API_BASE_URL
    }

    fun setBaseUrl(url: String) {
        prefs.edit().putString(KEY_BASE_URL, url).apply()
    }

    fun getSessionId(): String {
        return prefs.getString(KEY_SESSION_ID, "") ?: ""
    }

    fun getAuthToken(): String? {
        val token = prefs.getString(KEY_AUTH_TOKEN, null)
        return if (token.isNullOrBlank()) null else token
    }

    fun setAuthToken(token: String?) {
        prefs.edit().putString(KEY_AUTH_TOKEN, token).apply()
    }

    fun getUsername(): String? {
        val user = prefs.getString(KEY_USERNAME, null)
        return if (user.isNullOrBlank()) null else user
    }

    fun setUsername(user: String?) {
        prefs.edit().putString(KEY_USERNAME, user).apply()
    }

    fun isLoggedIn(): Boolean {
        return getAuthToken() != null
    }

    fun clearAuth() {
        prefs.edit()
            .remove(KEY_AUTH_TOKEN)
            .remove(KEY_USERNAME)
            .apply()
    }

    fun getRecommendationCount(): Int {
        return prefs.getInt(KEY_REC_COUNT, 10)
    }

    fun setRecommendationCount(count: Int) {
        prefs.edit().putInt(KEY_REC_COUNT, count).apply()
    }

    fun getThemeAccent(): String {
        return prefs.getString(KEY_THEME_ACCENT, "teal") ?: "teal"
    }

    fun setThemeAccent(accent: String) {
        prefs.edit().putString(KEY_THEME_ACCENT, accent).apply()
    }
}
