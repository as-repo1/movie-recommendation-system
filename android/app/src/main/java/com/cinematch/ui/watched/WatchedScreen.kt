package com.cinematch.ui.watched

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.cinematch.data.api.Movie
import com.cinematch.data.api.RetrofitClient
import com.cinematch.data.repository.WatchedRepository
import com.cinematch.ui.components.MovieCard
import com.cinematch.ui.components.MovieCardSkeleton
import com.cinematch.ui.theme.TextMuted
import kotlinx.coroutines.launch

@Composable
fun WatchedScreen(
    watchedRepo: WatchedRepository,
    onMovieClick: (Int) -> Unit,
) {
    val scope = rememberCoroutineScope()
    val entries = remember { watchedRepo.getWatched().toList() }  // List<Pair<Int, WatchedEntry>>
    val movies  = remember { mutableStateListOf<Movie>() }
    var loading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        entries.forEach { (id, _) ->
            scope.launch {
                try { movies.add(RetrofitClient.api.getMovie(id)) } catch (_: Exception) {}
            }
        }
        loading = false
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text("Watched", style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.padding(bottom = 12.dp))

        if (entries.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("✅", style = MaterialTheme.typography.displayMedium)
                    Spacer(Modifier.height(8.dp))
                    Text("No watched movies yet", color = TextMuted)
                }
            }
        } else if (loading && movies.isEmpty()) {
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) { items(entries.size) { MovieCardSkeleton() } }
        } else {
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(movies) { movie ->
                    MovieCard(
                        movie = movie,
                        myRating = watchedRepo.getRating(movie.id),
                        onClick  = { onMovieClick(movie.id) }
                    )
                }
            }
        }
    }
}
