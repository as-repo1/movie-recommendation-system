package com.cinematch.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cinematch.data.api.Movie
import com.cinematch.data.api.PersonalisedRequest
import com.cinematch.data.api.RatedMovie
import com.cinematch.data.api.RetrofitClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class HomeUiState {
    object Loading : HomeUiState()
    data class Success(val popular: List<Movie>, val personalised: List<Movie> = emptyList()) : HomeUiState()
    data class Error(val message: String) : HomeUiState()
}

class HomeViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<HomeUiState>(HomeUiState.Loading)
    val uiState: StateFlow<HomeUiState> = _uiState

    fun load(ratedMovies: List<Pair<Int, Float>>) {
        viewModelScope.launch {
            try {
                val popular = RetrofitClient.api.getPopular()
                val personalised = if (ratedMovies.isNotEmpty()) {
                    try {
                        RetrofitClient.api.getPersonalised(
                            PersonalisedRequest(
                                ratings = ratedMovies.map { RatedMovie(it.first, it.second) },
                                n = 12
                            )
                        ).recommendations
                    } catch (e: Exception) {
                        emptyList()
                    }
                } else emptyList()

                _uiState.value = HomeUiState.Success(popular, personalised)
            } catch (e: Exception) {
                _uiState.value = HomeUiState.Error(e.message ?: "Unknown error")
            }
        }
    }
}
