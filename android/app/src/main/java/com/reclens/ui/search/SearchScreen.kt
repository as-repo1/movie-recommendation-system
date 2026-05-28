package com.reclens.ui.search

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.reclens.data.repository.WatchlistRepository
import com.reclens.data.repository.WatchedRepository
import com.reclens.ui.components.MovieCard
import com.reclens.ui.components.MovieCardSkeleton
import com.reclens.ui.theme.TextMuted
import kotlinx.coroutines.launch

@Composable
fun SearchScreen(
    watchlistRepo: WatchlistRepository,
    watchedRepo: WatchedRepository,
    onMovieClick: (Int) -> Unit,
) {
    val vm: SearchViewModel = viewModel()
    val query by vm.query.collectAsState()
    val results by vm.results.collectAsState()
    val loading by vm.loading.collectAsState()
    val scope = rememberCoroutineScope()
    var localWatchlistVersion by remember { mutableIntStateOf(0) }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        OutlinedTextField(
            value = query,
            onValueChange = vm::setQuery,
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("Search movies…", color = TextMuted) },
            leadingIcon = { Icon(Icons.Default.Search, null) },
            singleLine = true,
            shape = MaterialTheme.shapes.medium,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = MaterialTheme.colorScheme.primary,
                unfocusedBorderColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)
            )
        )

        Spacer(Modifier.height(16.dp))

        when {
            loading -> {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) { items(6) { MovieCardSkeleton() } }
            }

            results.isEmpty() && query.length >= 2 -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("No results for \"$query\"", color = TextMuted)
                }
            }

            results.isNotEmpty() -> {
                // Key the grid with localWatchlistVersion to force recomposition when watchlist items are toggled
                key(localWatchlistVersion) {
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(2),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(results, key = { it.id }) { movie ->
                            MovieCard(
                                movie = movie,
                                isInWatchlist = watchlistRepo.isInWatchlist(movie.id),
                                myRating = watchedRepo.getRating(movie.id),
                                onWatchlistToggle = {
                                    scope.launch {
                                        if (watchlistRepo.isInWatchlist(movie.id)) {
                                            watchlistRepo.removeFromWatchlist(movie.id)
                                        } else {
                                            watchlistRepo.addToWatchlist(movie.id)
                                        }
                                        localWatchlistVersion++
                                    }
                                },
                                onClick = { onMovieClick(movie.id) }
                            )
                        }
                    }
                }
            }

            else -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Type to search for movies", color = TextMuted)
                }
            }
        }
    }
}
