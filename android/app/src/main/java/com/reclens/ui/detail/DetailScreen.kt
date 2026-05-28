package com.reclens.ui.detail

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.reclens.data.api.Movie
import com.reclens.data.api.RetrofitClient
import com.reclens.data.api.WatchlistRequest
import com.reclens.data.api.WatchedRequest
import com.reclens.data.repository.WatchlistRepository
import com.reclens.data.repository.WatchedRepository
import com.reclens.ui.components.MovieCard
import com.reclens.ui.theme.Gold
import com.reclens.ui.theme.TextMuted
import kotlinx.coroutines.launch

private const val PLACEHOLDER = "https://via.placeholder.com/300x450/2e3440/88c0d0?text=No+Poster"

@Composable
fun DetailScreen(
    movieId: Int,
    watchlistRepo: WatchlistRepository,
    watchedRepo: WatchedRepository,
    onBack: () -> Unit,
    onMovieClick: (Int) -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var movie by remember { mutableStateOf<Movie?>(null) }
    var similar by remember { mutableStateOf<List<Movie>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var showRatingDialog by remember { mutableStateOf(false) }
    var pendingRating by remember { mutableStateOf(7f) }

    var inWatchlist by remember { mutableStateOf(watchlistRepo.isInWatchlist(movieId)) }
    var isWatched by remember { mutableStateOf(watchedRepo.isWatched(movieId)) }
    var myRating by remember { mutableStateOf(watchedRepo.getRating(movieId)) }

    // Dynamically query API for details when movieId changes
    LaunchedEffect(movieId) {
        loading = true
        try {
            val api = RetrofitClient.getApi(context)
            movie = api.getMovie(movieId)
            similar = api.getSimilar(movieId).recommendations
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            loading = false
        }
    }

    if (showRatingDialog) {
        AlertDialog(
            onDismissRequest = { showRatingDialog = false },
            title = { Text("Rate this movie") },
            text = {
                Column {
                    Text("Tap a star to rate:", color = TextMuted, fontSize = 13.sp)
                    Spacer(Modifier.height(12.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        (1..10).forEach { star ->
                            Icon(
                                imageVector = if (star <= pendingRating) Icons.Default.Star else Icons.Default.StarBorder,
                                contentDescription = null,
                                tint = if (star <= pendingRating) Gold else TextMuted,
                                modifier = Modifier
                                    .size(24.dp)
                                    .weight(1f)
                                    .clickable { pendingRating = star.toFloat() }
                            )
                        }
                    }
                    Spacer(Modifier.height(12.dp))
                    Text("${pendingRating.toInt()}/10", color = Gold, fontWeight = FontWeight.Bold)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    scope.launch {
                        watchedRepo.markWatched(movieId, pendingRating)
                        watchlistRepo.removeFromWatchlist(movieId)
                        myRating = pendingRating
                        isWatched = true
                        inWatchlist = false
                        showRatingDialog = false
                    }
                }) { Text("Save") }
            },
            dismissButton = {
                TextButton(onClick = { showRatingDialog = false }) { Text("Cancel") }
            }
        )
    }

    if (loading) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
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
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.verticalGradient(
                            listOf(Color.Transparent, MaterialTheme.colorScheme.background)
                        )
                    )
            )
            IconButton(
                onClick = onBack, 
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(8.dp)
                    .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(50.dp))
            ) {
                Icon(Icons.Default.ArrowBack, "Back", tint = Color.White)
            }
        }

        // Main Content Area
        Column(modifier = Modifier.padding(horizontal = 16.dp)) {
            Row(modifier = Modifier.offset(y = (-40).dp), verticalAlignment = Alignment.Bottom) {
                AsyncImage(
                    model = m.posterUrl.ifEmpty { PLACEHOLDER },
                    contentDescription = m.title,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .width(100.dp)
                        .height(150.dp)
                        .clip(RoundedCornerShape(10.dp))
                )
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.padding(bottom = 8.dp)) {
                    Text(
                        m.title, 
                        style = MaterialTheme.typography.titleMedium, 
                        fontWeight = FontWeight.Bold, 
                        lineHeight = 22.sp
                    )
                    m.year?.let { Text("$it", color = TextMuted, fontSize = 13.sp) }
                    Spacer(Modifier.height(4.dp))
                    if (m.voteAverage > 0) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Star, null, tint = Gold, modifier = Modifier.size(14.dp))
                            Text(" ${"%.1f".format(m.voteAverage)}/10", color = Gold, fontSize = 13.sp)
                        }
                    }
                }
            }

            // Genres List
            if (m.genres.isNotEmpty()) {
                Row(
                    modifier = Modifier
                        .padding(bottom = 12.dp)
                        .offset(y = (-30).dp), 
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    m.genres.take(4).forEach { g ->
                        Surface(
                            shape = RoundedCornerShape(20.dp), 
                            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)
                        ) {
                            Text(
                                text = g, 
                                color = MaterialTheme.colorScheme.primary, 
                                fontSize = 11.sp, 
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                            )
                        }
                    }
                }
            }

            // Overview Section
            if (m.overview.isNotEmpty()) {
                Text(
                    text = "Overview", 
                    style = MaterialTheme.typography.titleSmall, 
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 6.dp)
                )
                Text(
                    text = m.overview, 
                    color = TextMuted, 
                    lineHeight = 22.sp, 
                    fontSize = 14.sp, 
                    modifier = Modifier.padding(bottom = 16.dp)
                )
            }

            // Extended Metadata: Director & Writer
            if (m.director.isNotEmpty() || m.writer.isNotEmpty() || m.cast.isNotEmpty()) {
                Text(
                    text = "Details", 
                    style = MaterialTheme.typography.titleSmall, 
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 8.dp)
                )

                if (m.director.isNotEmpty()) {
                    Row(modifier = Modifier.padding(bottom = 6.dp)) {
                        Text("Director: ", color = TextMuted, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                        Text(m.director, color = MaterialTheme.colorScheme.onSurface, fontSize = 13.sp)
                    }
                }

                if (m.writer.isNotEmpty()) {
                    Row(modifier = Modifier.padding(bottom = 6.dp)) {
                        Text("Writer: ", color = TextMuted, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                        Text(m.writer, color = MaterialTheme.colorScheme.onSurface, fontSize = 13.sp)
                    }
                }

                if (m.cast.isNotEmpty()) {
                    Text(
                        "Cast", 
                        color = TextMuted, 
                        fontSize = 13.sp, 
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(top = 4.dp, bottom = 6.dp)
                    )
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 16.dp)
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        m.cast.forEach { actor ->
                            Surface(
                                shape = RoundedCornerShape(8.dp), 
                                color = MaterialTheme.colorScheme.surfaceVariant
                            ) {
                                Text(
                                    text = actor, 
                                    color = MaterialTheme.colorScheme.onSurfaceVariant, 
                                    fontSize = 12.sp, 
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                                )
                            }
                        }
                    }
                }
            }

            // Action buttons (Watchlist & Watched)
            Row(modifier = Modifier.padding(bottom = 20.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            if (inWatchlist) {
                                watchlistRepo.removeFromWatchlist(movieId)
                            } else {
                                watchlistRepo.addToWatchlist(movieId)
                            }
                            inWatchlist = !inWatchlist
                        }
                    },
                    modifier = Modifier.weight(1f),
                    border = ButtonDefaults.outlinedButtonBorder.copy(
                        brush = Brush.linearGradient(
                            listOf(
                                if (inWatchlist) MaterialTheme.colorScheme.primary else Color.Gray, 
                                if (inWatchlist) MaterialTheme.colorScheme.primary else Color.Gray
                            )
                        )
                    )
                ) {
                    Icon(
                        imageVector = if (inWatchlist) Icons.Default.Bookmark else Icons.Default.BookmarkBorder,
                        contentDescription = null, 
                        tint = if (inWatchlist) MaterialTheme.colorScheme.primary else TextMuted,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = if (inWatchlist) "In Watchlist" else "Add to Watchlist",
                        color = if (inWatchlist) MaterialTheme.colorScheme.primary else TextMuted, 
                        fontSize = 13.sp
                    )
                }

                Button(
                    onClick = { pendingRating = myRating ?: 7f; showRatingDialog = true },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isWatched) Color(0xFF166534) else MaterialTheme.colorScheme.primary
                    )
                ) {
                    Icon(Icons.Default.Visibility, null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = if (isWatched) "Watched · ${myRating?.toInt()}/10" else "Mark as Watched",
                        fontSize = 13.sp
                    )
                }
            }

            // Similar Movies Section
            if (similar.isNotEmpty()) {
                Text(
                    text = "Similar Movies", 
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 12.dp)
                )
                Column(
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    val rows = similar.take(6).chunked(3)
                    rows.forEach { rowItems ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            rowItems.forEach { sm ->
                                Box(modifier = Modifier.weight(1f)) {
                                    MovieCard(
                                        movie = sm,
                                        isInWatchlist = watchlistRepo.isInWatchlist(sm.id),
                                        myRating = watchedRepo.getRating(sm.id),
                                        onWatchlistToggle = {
                                            scope.launch {
                                                if (watchlistRepo.isInWatchlist(sm.id)) {
                                                    watchlistRepo.removeFromWatchlist(sm.id)
                                                } else {
                                                    watchlistRepo.addToWatchlist(sm.id)
                                                }
                                            }
                                        },
                                        onClick = { onMovieClick(sm.id) }
                                    )
                                }
                            }
                            if (rowItems.size < 3) {
                                repeat(3 - rowItems.size) {
                                    Spacer(modifier = Modifier.weight(1f))
                                }
                            }
                        }
                    }
                }
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}
