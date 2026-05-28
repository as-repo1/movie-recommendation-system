package com.reclens.ui.home

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.reclens.data.repository.WatchlistRepository
import com.reclens.data.repository.WatchedRepository
import com.reclens.ui.components.MovieCard
import com.reclens.ui.components.MovieCardSkeleton
import com.reclens.ui.theme.TextMuted
import kotlinx.coroutines.launch

@Composable
fun HomeScreen(
    watchlistRepo: WatchlistRepository,
    watchedRepo: WatchedRepository,
    onMovieClick: (Int) -> Unit,
) {
    val vm: HomeViewModel = viewModel()
    val state by vm.uiState.collectAsState()
    val scope = rememberCoroutineScope()

    // Trigger syncing on mount to catch updates
    LaunchedEffect(Unit) {
        scope.launch {
            watchlistRepo.syncWithBackend()
            watchedRepo.syncWithBackend()
            val rated = watchedRepo.getWatched().map { (id, entry) -> Pair(id, entry.rating) }
            vm.load(rated)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Text(
            "Popular Movies",
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
            modifier = Modifier.padding(bottom = 16.dp)
        )

        when (val s = state) {
            is HomeUiState.Loading -> {
                Column(verticalArrangement = Arrangement.spacedBy(20.dp)) {
                    Text(
                        text = "🎯 For You",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                        color = MaterialTheme.colorScheme.primary
                    )
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        items(5) {
                            Box(modifier = Modifier.width(140.dp)) {
                                MovieCardSkeleton()
                            }
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = "🔥 Trending",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold)
                    )
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        items(5) {
                            Box(modifier = Modifier.width(140.dp)) {
                                MovieCardSkeleton()
                            }
                        }
                    }
                }
            }

            is HomeUiState.Error -> {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(300.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(s.message, color = TextMuted)
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = {
                            scope.launch {
                                val rated = watchedRepo.getWatched().map { (id, entry) -> Pair(id, entry.rating) }
                                vm.load(rated)
                            }
                        }) { Text("Retry") }
                    }
                }
            }

            is HomeUiState.Success -> {
                var localWatchlistVersion by remember { mutableIntStateOf(0) }

                Column(verticalArrangement = Arrangement.spacedBy(24.dp)) {
                    if (s.personalised.isNotEmpty()) {
                        Column {
                            Text(
                                text = "🎯 For You",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                                color = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.padding(bottom = 12.dp)
                            )
                            // Recommended movies horizontal row
                            key(localWatchlistVersion) {
                                LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                    items(s.personalised, key = { "personalised_${it.id}" }) { movie ->
                                        Box(modifier = Modifier.width(140.dp)) {
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
                        }
                    }

                    Column {
                        Text(
                            text = "🔥 Trending",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                            modifier = Modifier.padding(bottom = 12.dp)
                        )
                        // Trending movies horizontal row
                        key(localWatchlistVersion) {
                            LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                items(s.popular, key = { "popular_${it.id}" }) { movie ->
                                    Box(modifier = Modifier.width(140.dp)) {
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
                    }
                }
            }
        }
    }
}
