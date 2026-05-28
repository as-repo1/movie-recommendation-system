package com.reclens.ui.watched

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Sort
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.reclens.data.api.Movie
import com.reclens.data.api.RetrofitClient
import com.reclens.data.repository.WatchedRepository
import com.reclens.data.repository.WatchedEntry
import com.reclens.ui.components.MovieCard
import com.reclens.ui.components.MovieCardSkeleton
import com.reclens.ui.theme.TextMuted
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.launch

enum class SortBy {
    DATE, RATING
}

@Composable
fun WatchedScreen(
    watchedRepo: WatchedRepository,
    onMovieClick: (Int) -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    
    // Sort parameter
    var sortBy by remember { mutableStateOf(SortBy.DATE) }
    
    // Remote lists loaded
    val movies = remember { mutableStateListOf<Movie>() }
    var loading by remember { mutableStateOf(true) }

    // Sync & Load
    LaunchedEffect(Unit) {
        scope.launch {
            loading = true
            watchedRepo.syncWithBackend()
            
            val entries = watchedRepo.getWatched().toList()
            movies.clear()
            
            try {
                val api = RetrofitClient.getApi(context)
                val deferredMovies = entries.map { (id, _) ->
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

    // Sort function
    val sortedMovies = remember(movies.size, sortBy) {
        val ratings = watchedRepo.getWatched()
        when (sortBy) {
            SortBy.RATING -> {
                movies.sortedByDescending { ratings[it.id]?.rating ?: 0f }
            }
            SortBy.DATE -> {
                movies.sortedByDescending { ratings[it.id]?.addedAt ?: 0L }
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        // Title & Header Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Watched", 
                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
            )

            // Sorting Controls
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Sort, 
                    contentDescription = "Sort", 
                    tint = TextMuted, 
                    modifier = Modifier.size(16.dp)
                )
                Text("Sort:", color = TextMuted, fontSize = 12.sp)

                // Date sort selection button
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = if (sortBy == SortBy.DATE) MaterialTheme.colorScheme.primary.copy(alpha = 0.15f) else MaterialTheme.colorScheme.surface,
                    modifier = Modifier.clickable { sortBy = SortBy.DATE }
                ) {
                    Text(
                        text = "Date",
                        color = if (sortBy == SortBy.DATE) MaterialTheme.colorScheme.primary else TextMuted,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }

                // Rating sort selection button
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = if (sortBy == SortBy.RATING) MaterialTheme.colorScheme.primary.copy(alpha = 0.15f) else MaterialTheme.colorScheme.surface,
                    modifier = Modifier.clickable { sortBy = SortBy.RATING }
                ) {
                    Text(
                        text = "Rating",
                        color = if (sortBy == SortBy.RATING) MaterialTheme.colorScheme.primary else TextMuted,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }
        }

        Spacer(Modifier.height(16.dp))

        if (loading && movies.isEmpty()) {
            val watchedIds = remember { watchedRepo.getWatched().keys.toList() }
            if (watchedIds.isEmpty()) {
                EmptyWatchedState()
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(watchedIds.size) { MovieCardSkeleton() }
                }
            }
        } else if (movies.isEmpty()) {
            EmptyWatchedState()
        } else {
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(sortedMovies, key = { it.id }) { movie ->
                    Box(modifier = Modifier.fillMaxWidth()) {
                        MovieCard(
                            movie = movie,
                            myRating = watchedRepo.getRating(movie.id),
                            onClick = { onMovieClick(movie.id) }
                        )

                        // Trash/Delete Icon overlay to remove from watched list
                        IconButton(
                            onClick = {
                                scope.launch {
                                    watchedRepo.removeWatched(movie.id)
                                    movies.remove(movie)
                                }
                            },
                            modifier = Modifier
                                .align(Alignment.TopStart)
                                .padding(6.dp)
                                .size(28.dp)
                                .background(Color.Red.copy(alpha = 0.8f), RoundedCornerShape(6.dp))
                        ) {
                            Icon(
                                imageVector = Icons.Default.Delete,
                                contentDescription = "Remove",
                                tint = Color.White,
                                modifier = Modifier.size(14.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun EmptyWatchedState() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("✅", style = MaterialTheme.typography.displayMedium)
            Spacer(Modifier.height(8.dp))
            Text("No watched movies yet", color = TextMuted)
        }
    }
}
