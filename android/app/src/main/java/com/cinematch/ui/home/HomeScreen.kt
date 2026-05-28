package com.cinematch.ui.home

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.cinematch.data.repository.WatchlistRepository
import com.cinematch.data.repository.WatchedRepository
import com.cinematch.ui.components.MovieCard
import com.cinematch.ui.components.MovieCardSkeleton
import com.cinematch.ui.theme.Purple80
import com.cinematch.ui.theme.TextMuted

@Composable
fun HomeScreen(
    watchlistRepo: WatchlistRepository,
    watchedRepo: WatchedRepository,
    onMovieClick: (Int) -> Unit,
) {
    val vm: HomeViewModel = viewModel()
    val state by vm.uiState.collectAsState()

    LaunchedEffect(Unit) {
        val rated = watchedRepo.getWatched().map { (id, entry) -> Pair(id, entry.rating) }
        vm.load(rated)
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(
            "Popular Movies",
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
            modifier = Modifier.padding(bottom = 12.dp)
        )

        when (val s = state) {
            is HomeUiState.Loading -> {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(8) { MovieCardSkeleton() }
                }
            }

            is HomeUiState.Error -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("Failed to load movies", color = TextMuted)
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = { vm.load(emptyList()) }) { Text("Retry") }
                    }
                }
            }

            is HomeUiState.Success -> {
                if (s.personalised.isNotEmpty()) {
                    Text("🎯 For You", style = MaterialTheme.typography.titleMedium, color = Purple80,
                        modifier = Modifier.padding(bottom = 8.dp))
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(2),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.height(320.dp)
                    ) {
                        items(s.personalised.take(4)) { movie ->
                            MovieCard(
                                movie = movie,
                                isInWatchlist = watchlistRepo.isInWatchlist(movie.id),
                                myRating = watchedRepo.getRating(movie.id),
                                onWatchlistToggle = {
                                    if (watchlistRepo.isInWatchlist(movie.id))
                                        watchlistRepo.removeFromWatchlist(movie.id)
                                    else watchlistRepo.addToWatchlist(movie.id)
                                },
                                onClick = { onMovieClick(movie.id) }
                            )
                        }
                    }
                    Spacer(Modifier.height(16.dp))
                    Text("🔥 Trending", style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(bottom = 8.dp))
                }

                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(s.popular) { movie ->
                        MovieCard(
                            movie = movie,
                            isInWatchlist = watchlistRepo.isInWatchlist(movie.id),
                            myRating = watchedRepo.getRating(movie.id),
                            onWatchlistToggle = {
                                if (watchlistRepo.isInWatchlist(movie.id))
                                    watchlistRepo.removeFromWatchlist(movie.id)
                                else watchlistRepo.addToWatchlist(movie.id)
                            },
                            onClick = { onMovieClick(movie.id) }
                        )
                    }
                }
            }
        }
    }
}
