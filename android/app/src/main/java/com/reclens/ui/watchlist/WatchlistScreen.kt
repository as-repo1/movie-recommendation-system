package com.reclens.ui.watchlist

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.reclens.data.api.Movie
import com.reclens.data.api.RetrofitClient
import com.reclens.data.repository.WatchlistRepository
import com.reclens.data.repository.WatchedRepository
import com.reclens.ui.components.MovieCard
import com.reclens.ui.components.MovieCardSkeleton
import com.reclens.ui.theme.TextMuted
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.launch

@Composable
fun WatchlistScreen(
    watchlistRepo: WatchlistRepository,
    watchedRepo: WatchedRepository,
    onMovieClick: (Int) -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val movies = remember { mutableStateListOf<Movie>() }
    var loading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        scope.launch {
            loading = true
            // Sync local DB cache with backend state first
            watchlistRepo.syncWithBackend()
            watchedRepo.syncWithBackend()
            
            val ids = watchlistRepo.getWatchlist().toList()
            movies.clear()
            
            try {
                val api = RetrofitClient.getApi(context)
                // Fetch movie details concurrently using async-awaitAll
                val deferredMovies = ids.map { id ->
                    async {
                        try {
                            api.getMovie(id)
                        } catch (e: Exception) {
                            null
                        }
                    }
                }
                val fetched = deferredMovies.awaitAll().filterNotNull()
                movies.addAll(fetched)
            } catch (e: Exception) {
                e.printStackTrace()
            } finally {
                loading = false
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(
            text = "Watchlist", 
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
            modifier = Modifier.padding(bottom = 12.dp)
        )

        if (loading && movies.isEmpty()) {
            val watchlistIds = remember { watchlistRepo.getWatchlist().toList() }
            if (watchlistIds.isEmpty()) {
                EmptyWatchlistState()
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(watchlistIds.size) { MovieCardSkeleton() }
                }
            }
        } else if (movies.isEmpty()) {
            EmptyWatchlistState()
        } else {
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(movies, key = { it.id }) { movie ->
                    MovieCard(
                        movie = movie,
                        isInWatchlist = true,
                        myRating = watchedRepo.getRating(movie.id),
                        onWatchlistToggle = {
                            scope.launch {
                                watchlistRepo.removeFromWatchlist(movie.id)
                                movies.remove(movie)
                            }
                        },
                        onClick = { onMovieClick(movie.id) }
                    )
                }
            }
        }
    }
}

@Composable
fun EmptyWatchlistState() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("🎬", style = MaterialTheme.typography.displayMedium)
            Spacer(Modifier.height(8.dp))
            Text("Your watchlist is empty", color = TextMuted)
        }
    }
}
