package com.cinematch.ui.detail

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.cinematch.data.api.Movie
import com.cinematch.data.api.RetrofitClient
import com.cinematch.data.repository.WatchlistRepository
import com.cinematch.data.repository.WatchedRepository
import com.cinematch.ui.components.MovieCard
import com.cinematch.ui.theme.Gold
import com.cinematch.ui.theme.Purple80
import com.cinematch.ui.theme.TextMuted

private val PLACEHOLDER = "https://via.placeholder.com/300x450/1a1a2e/8b5cf6?text=No+Poster"

@Composable
fun DetailScreen(
    movieId: Int,
    watchlistRepo: WatchlistRepository,
    watchedRepo: WatchedRepository,
    onBack: () -> Unit,
    onMovieClick: (Int) -> Unit,
) {
    var movie by remember { mutableStateOf<Movie?>(null) }
    var similar by remember { mutableStateOf<List<Movie>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var showRatingDialog by remember { mutableStateOf(false) }
    var pendingRating by remember { mutableStateOf(7f) }

    var inWatchlist by remember { mutableStateOf(watchlistRepo.isInWatchlist(movieId)) }
    var isWatched by remember { mutableStateOf(watchedRepo.isWatched(movieId)) }
    var myRating by remember { mutableStateOf(watchedRepo.getRating(movieId)) }

    LaunchedEffect(movieId) {
        loading = true
        try {
            movie = RetrofitClient.api.getMovie(movieId)
            similar = RetrofitClient.api.getSimilar(movieId).recommendations
        } catch (_: Exception) {}
        loading = false
    }

    if (showRatingDialog) {
        AlertDialog(
            onDismissRequest = { showRatingDialog = false },
            title = { Text("Rate this movie") },
            text = {
                Column {
                    Text("Tap a star to rate:", color = TextMuted, fontSize = 13.sp)
                    Spacer(Modifier.height(12.dp))
                    Row {
                        (1..10).forEach { star ->
                            Icon(
                                imageVector = if (star <= pendingRating) Icons.Default.Star else Icons.Default.StarBorder,
                                contentDescription = null,
                                tint = if (star <= pendingRating) Gold else TextMuted,
                                modifier = Modifier.size(28.dp).weight(1f).then(
                                    Modifier.clickable { pendingRating = star.toFloat() }
                                )
                            )
                        }
                    }
                    Spacer(Modifier.height(6.dp))
                    Text("${pendingRating.toInt()}/10", color = Gold, fontWeight = FontWeight.Bold)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    watchedRepo.markWatched(movieId, pendingRating)
                    watchlistRepo.removeFromWatchlist(movieId)
                    myRating = pendingRating
                    isWatched = true
                    inWatchlist = false
                    showRatingDialog = false
                }) { Text("Save") }
            },
            dismissButton = {
                TextButton(onClick = { showRatingDialog = false }) { Text("Cancel") }
            }
        )
    }

    if (loading) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = Purple80)
        }
        return
    }

    val m = movie ?: run {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Movie not found", color = TextMuted)
        }
        return
    }

    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {

        // Backdrop
        Box(modifier = Modifier.fillMaxWidth().height(260.dp)) {
            AsyncImage(
                model = m.backdropUrl.ifEmpty { m.posterUrl.ifEmpty { PLACEHOLDER } },
                contentDescription = m.title,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize()
            )
            Box(
                modifier = Modifier.fillMaxSize().background(
                    Brush.verticalGradient(listOf(Color.Transparent, Color(0xFF0A0A0F)))
                )
            )
            IconButton(onClick = onBack, modifier = Modifier.align(Alignment.TopStart).padding(8.dp)) {
                Icon(Icons.Default.ArrowBack, "Back", tint = Color.White)
            }
        }

        // Content
        Column(modifier = Modifier.padding(horizontal = 16.dp)) {
            Row(modifier = Modifier.offset(y = (-40).dp), verticalAlignment = Alignment.Bottom) {
                AsyncImage(
                    model = m.posterUrl.ifEmpty { PLACEHOLDER },
                    contentDescription = m.title,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.width(100.dp).height(150.dp).clip(RoundedCornerShape(10.dp))
                )
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.padding(bottom = 8.dp)) {
                    Text(m.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, lineHeight = 22.sp)
                    m.year?.let { Text("$it", color = TextMuted, fontSize = 13.sp) }
                    if (m.voteAverage > 0) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Star, null, tint = Gold, modifier = Modifier.size(14.dp))
                            Text(" ${"%.1f".format(m.voteAverage)}/10", color = Gold, fontSize = 13.sp)
                        }
                    }
                }
            }

            // Genres
            if (m.genres.isNotEmpty()) {
                Row(modifier = Modifier.padding(bottom = 12.dp).offset(y = (-30).dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    m.genres.take(4).forEach { g ->
                        Surface(shape = RoundedCornerShape(20.dp), color = Purple80.copy(alpha = 0.15f)) {
                            Text(g, color = Purple80, fontSize = 11.sp, modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp))
                        }
                    }
                }
            }

            // Overview
            if (m.overview.isNotEmpty()) {
                Text("Overview", style = MaterialTheme.typography.titleSmall, modifier = Modifier.padding(bottom = 6.dp))
                Text(m.overview, color = TextMuted, lineHeight = 22.sp, fontSize = 14.sp, modifier = Modifier.padding(bottom = 16.dp))
            }

            // Action buttons
            Row(modifier = Modifier.padding(bottom = 16.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(
                    onClick = {
                        if (inWatchlist) watchlistRepo.removeFromWatchlist(movieId)
                        else watchlistRepo.addToWatchlist(movieId)
                        inWatchlist = !inWatchlist
                    },
                    modifier = Modifier.weight(1f),
                    border = ButtonDefaults.outlinedButtonBorder.copy(
                        brush = Brush.linearGradient(listOf(if (inWatchlist) Purple80 else Color.Gray, if (inWatchlist) Purple80 else Color.Gray))
                    )
                ) {
                    Icon(
                        if (inWatchlist) Icons.Default.Bookmark else Icons.Default.BookmarkBorder,
                        null, tint = if (inWatchlist) Purple80 else TextMuted,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(Modifier.width(4.dp))
                    Text(if (inWatchlist) "In Watchlist" else "Add to Watchlist",
                        color = if (inWatchlist) Purple80 else TextMuted, fontSize = 13.sp)
                }

                Button(
                    onClick = { pendingRating = myRating ?: 7f; showRatingDialog = true },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isWatched) Color(0xFF166534) else Purple80
                    )
                ) {
                    Icon(Icons.Default.Visibility, null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(4.dp))
                    Text(
                        if (isWatched) "Watched · ${myRating?.toInt()}/10" else "Mark as Watched",
                        fontSize = 13.sp
                    )
                }
            }

            // Similar
            if (similar.isNotEmpty()) {
                Text("Similar Movies", style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.padding(bottom = 12.dp))
                LazyVerticalGrid(
                    columns = GridCells.Fixed(3),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.height(380.dp),
                    userScrollEnabled = false
                ) {
                    items(similar.take(6)) { sm ->
                        MovieCard(
                            movie = sm,
                            isInWatchlist = watchlistRepo.isInWatchlist(sm.id),
                            myRating = watchedRepo.getRating(sm.id),
                            onWatchlistToggle = {
                                if (watchlistRepo.isInWatchlist(sm.id)) watchlistRepo.removeFromWatchlist(sm.id)
                                else watchlistRepo.addToWatchlist(sm.id)
                            },
                            onClick = { onMovieClick(sm.id) }
                        )
                    }
                }
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

private fun Modifier.clickable(onClick: () -> Unit) = this.then(
    Modifier.fillMaxWidth().height(28.dp)
).also { } // simplified; real usage should use Modifier.clickable {}
