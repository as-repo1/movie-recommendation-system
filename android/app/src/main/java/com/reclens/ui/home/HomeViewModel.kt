package com.reclens.ui.home

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.reclens.data.api.Movie
import com.reclens.data.api.PersonalisedRequest
import com.reclens.data.api.RatedMovie
import com.reclens.data.api.RetrofitClient
import com.reclens.data.repository.SettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class HomeUiState {
    object Loading : HomeUiState()
    data class Success(val popular: List<Movie>, val personalised: List<Movie> = emptyList()) : HomeUiState()
    data class Error(val message: String) : HomeUiState()
}

class HomeViewModel(application: Application) : AndroidViewModel(application) {
    private val _uiState = MutableStateFlow<HomeUiState>(HomeUiState.Loading)
    val uiState: StateFlow<HomeUiState> = _uiState

    fun load(ratedMovies: List<Pair<Int, Float>>) {
        viewModelScope.launch {
            _uiState.value = HomeUiState.Loading
            try {
                val context = getApplication<Application>().applicationContext
                val api = RetrofitClient.getApi(context)
                val settings = SettingsRepository(context)
                val limit = settings.getRecommendationCount()

                val popular = api.getPopular(page = 1)
                val personalised = if (ratedMovies.isNotEmpty()) {
                    try {
                        api.getPersonalised(
                            PersonalisedRequest(
                                ratings = ratedMovies.map { RatedMovie(it.first, it.second) },
                                n = limit
                            )
                        ).recommendations
                    } catch (e: Exception) {
                        emptyList()
                    }
                } else emptyList()

                _uiState.value = HomeUiState.Success(popular, personalised)
            } catch (e: Exception) {
                _uiState.value = HomeUiState.Error(e.message ?: "Failed to connect to backend server")
            }
        }
    }
}
