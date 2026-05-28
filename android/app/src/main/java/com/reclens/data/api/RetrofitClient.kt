package com.reclens.data.api

import android.content.Context
import com.reclens.data.repository.SettingsRepository
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private var apiInstance: RecLensApi? = null
    private var lastBaseUrl: String? = null
    private var lastToken: String? = null

    /**
     * Retrieves the API instance, rebuilding it if the base URL or authorization token has changed.
     */
    fun getApi(context: Context): RecLensApi {
        val settings = SettingsRepository(context)
        val baseUrl = settings.getBaseUrl().trim().let {
            if (it.endsWith("/")) it else "$it/"
        }
        val token = settings.getAuthToken()
        val sessionId = settings.getSessionId()

        synchronized(this) {
            if (apiInstance == null || lastBaseUrl != baseUrl || lastToken != token) {
                val logging = HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BODY
                }

                val okHttp = OkHttpClient.Builder()
                    .addInterceptor(logging)
                    .addInterceptor { chain ->
                        val requestBuilder = chain.request().newBuilder()
                            .header("X-Session-ID", sessionId)
                            .header("Content-Type", "application/json")
                        
                        if (!token.isNullOrBlank()) {
                            requestBuilder.header("Authorization", "Bearer $token")
                        }
                        chain.proceed(requestBuilder.build())
                    }
                    .build()

                apiInstance = Retrofit.Builder()
                    .baseUrl(baseUrl)
                    .client(okHttp)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
                    .create(RecLensApi::class.java)

                lastBaseUrl = baseUrl
                lastToken = token
            }
            return apiInstance!!
        }
    }
}
