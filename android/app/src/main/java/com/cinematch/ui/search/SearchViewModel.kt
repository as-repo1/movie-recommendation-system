package com.cinematch.ui.search

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cinematch.data.api.Movie
import com.cinematch.data.api.RetrofitClient
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

@OptIn(FlowPreview::class)
class SearchViewModel : ViewModel() {
    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query

    private val _results = MutableStateFlow<List<Movie>>(emptyList())
    val results: StateFlow<List<Movie>> = _results

    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading

    init {
        viewModelScope.launch {
            _query.debounce(300)
                .filter { it.length >= 2 }
                .distinctUntilChanged()
                .collect { q ->
                    _loading.value = true
                    try {
                        _results.value = RetrofitClient.api.search(q).movies
                    } catch (e: Exception) {
                        _results.value = emptyList()
                    } finally {
                        _loading.value = false
                    }
                }
        }
    }

    fun setQuery(q: String) {
        _query.value = q
        if (q.length < 2) _results.value = emptyList()
    }
}
