package com.reclens

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.reclens.data.api.RetrofitClient
import com.reclens.data.repository.SettingsRepository
import com.reclens.data.repository.WatchlistRepository
import com.reclens.data.repository.WatchedRepository
import com.reclens.ui.components.AuthDialog
import com.reclens.ui.home.HomeScreen
import com.reclens.ui.search.SearchScreen
import com.reclens.ui.theme.*
import com.reclens.ui.watchlist.WatchlistScreen
import com.reclens.ui.watched.WatchedScreen
import com.reclens.ui.detail.DetailScreen
import kotlinx.coroutines.launch

sealed class Screen(val route: String, val label: String) {
    object Home      : Screen("home",      "Home")
    object Search    : Screen("search",    "Search")
    object Watchlist : Screen("watchlist", "Watchlist")
    object Watched   : Screen("watched",   "Watched")
    object Detail    : Screen("detail/{movieId}", "Detail") {
        fun createRoute(id: Int) = "detail/$id"
    }
}

class MainActivity : ComponentActivity() {
    @OptIn(ExperimentalMaterial3Api::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val watchlistRepo = WatchlistRepository(this)
        val watchedRepo   = WatchedRepository(this)
        val settingsRepo  = SettingsRepository(this)

        setContent {
            var currentAccent by remember { mutableStateOf(settingsRepo.getThemeAccent()) }
            var authVersion by remember { mutableIntStateOf(0) }

            RecLensTheme(accent = currentAccent) {
                val navController = rememberNavController()
                val currentBackStack by navController.currentBackStackEntryAsState()
                val currentRoute = currentBackStack?.destination?.route

                val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
                val scope = rememberCoroutineScope()
                val context = LocalContext.current

                // Auth dialog state
                var showAuthDialog by remember { mutableStateOf(false) }

                if (showAuthDialog) {
                    AuthDialog(
                        onDismiss = { showAuthDialog = false },
                        onSuccess = {
                            authVersion++
                            Toast.makeText(context, "Authenticated successfully!", Toast.LENGTH_SHORT).show()
                        }
                    )
                }

                // Modal Navigation Drawer enclosing Scaffold
                ModalNavigationDrawer(
                    drawerState = drawerState,
                    drawerContent = {
                        ModalDrawerSheet(
                            modifier = Modifier
                                .width(320.dp)
                                .fillMaxHeight()
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(20.dp)
                                    .verticalScroll(rememberScrollState())
                            ) {
                                // 1. Title / Header
                                Text(
                                    text = "🎬 RecLens",
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(vertical = 12.dp)
                                )
                                Text(
                                    text = "Settings & Customization",
                                    fontSize = 12.sp,
                                    color = TextMuted,
                                    modifier = Modifier.padding(bottom = 20.dp)
                                )
                                HorizontalDivider(color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))

                                key(authVersion) {
                                    // 2. User Account section
                                    Text(
                                        text = "Account",
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 14.sp,
                                        modifier = Modifier.padding(top = 16.dp, bottom = 8.dp)
                                    )

                                    if (settingsRepo.isLoggedIn()) {
                                        Text(
                                            text = "Logged in as: ${settingsRepo.getUsername()}",
                                            fontSize = 13.sp,
                                            fontWeight = FontWeight.SemiBold,
                                            modifier = Modifier.padding(bottom = 12.dp)
                                        )
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                                        ) {
                                            Button(
                                                onClick = {
                                                    scope.launch {
                                                        Toast.makeText(context, "Syncing...", Toast.LENGTH_SHORT).show()
                                                        watchlistRepo.syncWithBackend()
                                                        watchedRepo.syncWithBackend()
                                                        Toast.makeText(context, "Sync completed!", Toast.LENGTH_SHORT).show()
                                                    }
                                                },
                                                modifier = Modifier.weight(1f),
                                                contentPadding = PaddingValues(horizontal = 4.dp, vertical = 8.dp)
                                            ) {
                                                Icon(Icons.Default.Sync, null, modifier = Modifier.size(14.dp))
                                                Spacer(Modifier.width(4.dp))
                                                Text("Sync", fontSize = 12.sp)
                                            }

                                            OutlinedButton(
                                                onClick = {
                                                    settingsRepo.clearAuth()
                                                    authVersion++
                                                    Toast.makeText(context, "Logged out", Toast.LENGTH_SHORT).show()
                                                },
                                                modifier = Modifier.weight(1f),
                                                contentPadding = PaddingValues(horizontal = 4.dp, vertical = 8.dp)
                                            ) {
                                                Icon(Icons.Default.Logout, null, modifier = Modifier.size(14.dp))
                                                Spacer(Modifier.width(4.dp))
                                                Text("Logout", fontSize = 12.sp)
                                            }
                                        }
                                    } else {
                                        Text(
                                            text = "Sync ratings and watchlists across devices by signing in.",
                                            fontSize = 12.sp,
                                            color = TextMuted,
                                            modifier = Modifier.padding(bottom = 12.dp)
                                        )
                                        Button(
                                            onClick = { showAuthDialog = true },
                                            modifier = Modifier.fillMaxWidth()
                                        ) {
                                            Icon(Icons.Default.Login, null, modifier = Modifier.size(16.dp))
                                            Spacer(Modifier.width(6.dp))
                                            Text("Sign In / Register")
                                        }
                                    }
                                }

                                Spacer(Modifier.height(16.dp))
                                HorizontalDivider(color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))

                                // 3. Backend Configuration
                                Text(
                                    text = "Backend Server URL",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    modifier = Modifier.padding(top = 16.dp, bottom = 8.dp)
                                )
                                var serverUrlText by remember { mutableStateOf(settingsRepo.getBaseUrl()) }
                                OutlinedTextField(
                                    value = serverUrlText,
                                    onValueChange = { serverUrlText = it },
                                    singleLine = true,
                                    modifier = Modifier.fillMaxWidth(),
                                    textStyle = LocalTextStyle.current.copy(fontSize = 13.sp)
                                )
                                Spacer(Modifier.height(8.dp))
                                Button(
                                    onClick = {
                                        settingsRepo.setBaseUrl(serverUrlText.trim())
                                        Toast.makeText(context, "Base URL updated!", Toast.LENGTH_SHORT).show()
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text("Save Server Configuration")
                                }

                                Spacer(Modifier.height(16.dp))
                                HorizontalDivider(color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))

                                // 4. Custom Recommendations count Limit
                                Text(
                                    text = "Recommendations Limit",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    modifier = Modifier.padding(top = 16.dp, bottom = 4.dp)
                                )
                                var limitValue by remember { mutableFloatStateOf(settingsRepo.getRecommendationCount().toFloat()) }
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Slider(
                                        value = limitValue,
                                        onValueChange = {
                                            limitValue = it
                                            settingsRepo.setRecommendationCount(it.toInt())
                                        },
                                        valueRange = 5f..20f,
                                        steps = 2,
                                        modifier = Modifier.weight(1f)
                                    )
                                    Spacer(Modifier.width(8.dp))
                                    Text("${limitValue.toInt()}", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                }

                                Spacer(Modifier.height(12.dp))
                                HorizontalDivider(color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))

                                // 5. Theme Accent selector
                                Text(
                                    text = "Theme Accent Color",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    modifier = Modifier.padding(top = 16.dp, bottom = 12.dp)
                                )
                                val accents = listOf("teal", "blue", "purple", "green", "orange", "red")
                                val accentColors = listOf(AccentTeal, AccentBlue, AccentPurple, AccentGreen, AccentOrange, AccentRed)
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    accents.forEachIndexed { i, acc ->
                                        Box(
                                            modifier = Modifier
                                                .size(36.dp)
                                                .clip(CircleShape)
                                                .background(accentColors[i])
                                                .border(
                                                    width = if (currentAccent == acc) 3.dp else 0.dp,
                                                    color = Color.White,
                                                    shape = CircleShape
                                                )
                                                .clickable {
                                                    settingsRepo.setThemeAccent(acc)
                                                    currentAccent = acc
                                                }
                                        )
                                    }
                                }

                                Spacer(Modifier.height(20.dp))
                                HorizontalDivider(color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))

                                // 6. Latency Ping Tool
                                Text(
                                    text = "Connection Tester",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    modifier = Modifier.padding(top = 16.dp, bottom = 8.dp)
                                )
                                var pingResult by remember { mutableStateOf<String?>(null) }
                                var pinging by remember { mutableStateOf(false) }

                                Button(
                                    onClick = {
                                        scope.launch {
                                            pinging = true
                                            pingResult = "Pinging..."
                                            val startTime = System.currentTimeMillis()
                                            try {
                                                val api = RetrofitClient.getApi(context)
                                                val res = api.checkHealth()
                                                val duration = System.currentTimeMillis() - startTime
                                                pingResult = "Online • Latency: ${duration}ms\nContent Model: ${if (res.contentModel) "Loaded" else "Empty"}\nCollaborative Model: ${if (res.lightfmModel) "Loaded" else "Empty"}"
                                            } catch (e: Exception) {
                                                pingResult = "Offline • Connection Failed\nError: ${e.message ?: "Unknown"}"
                                            } finally {
                                                pinging = false
                                            }
                                        }
                                    },
                                    enabled = !pinging,
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text("Test Server Latency (Ping)")
                                }
                                pingResult?.let {
                                    Spacer(Modifier.height(8.dp))
                                    Surface(
                                        shape = RoundedCornerShape(6.dp),
                                        color = MaterialTheme.colorScheme.surfaceVariant,
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text(
                                            text = it,
                                            fontSize = 11.sp,
                                            lineHeight = 16.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            modifier = Modifier.padding(8.dp)
                                        )
                                    }
                                }
                            }
                        }
                    }
                ) {
                    val bottomTabs = listOf(Screen.Home, Screen.Search, Screen.Watchlist, Screen.Watched)

                    Scaffold(
                        modifier = Modifier.fillMaxSize(),
                        topBar = {
                            if (currentRoute?.startsWith("detail") == false) {
                                TopAppBar(
                                    title = { Text("RecLens", fontWeight = FontWeight.Bold) },
                                    navigationIcon = {
                                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                                            Icon(Icons.Default.Menu, contentDescription = "Menu")
                                        }
                                    },
                                    colors = TopAppBarDefaults.topAppBarColors(
                                        containerColor = MaterialTheme.colorScheme.surface
                                    )
                                )
                            }
                        },
                        bottomBar = {
                            if (currentRoute?.startsWith("detail") == false) {
                                NavigationBar {
                                    bottomTabs.forEach { screen ->
                                        val icon = when (screen) {
                                            Screen.Home      -> Icons.Default.Home
                                            Screen.Search    -> Icons.Default.Search
                                            Screen.Watchlist -> Icons.Default.Bookmark
                                            Screen.Watched   -> Icons.Default.CheckCircle
                                            else             -> Icons.Default.Home
                                        }
                                        val count = when (screen) {
                                            Screen.Watchlist -> watchlistRepo.getWatchlist().size
                                            Screen.Watched   -> watchedRepo.getWatched().size
                                            else             -> 0
                                        }
                                        NavigationBarItem(
                                            selected  = currentRoute == screen.route,
                                            onClick   = { navController.navigate(screen.route) { popUpTo(Screen.Home.route); launchSingleTop = true } },
                                            icon      = {
                                                BadgedBox(badge = { if (count > 0) Badge { Text("$count") } }) {
                                                    Icon(icon, screen.label)
                                                }
                                            },
                                            label     = { Text(screen.label) }
                                        )
                                    }
                                }
                            }
                        }
                    ) { innerPadding ->
                        NavHost(
                            navController = navController,
                            startDestination = Screen.Home.route,
                            modifier = Modifier.padding(innerPadding)
                        ) {
                            composable(Screen.Home.route) {
                                HomeScreen(
                                    watchlistRepo = watchlistRepo,
                                    watchedRepo   = watchedRepo,
                                    onMovieClick  = { navController.navigate(Screen.Detail.createRoute(it)) }
                                )
                            }
                            composable(Screen.Search.route) {
                                SearchScreen(
                                    watchlistRepo = watchlistRepo,
                                    watchedRepo   = watchedRepo,
                                    onMovieClick  = { navController.navigate(Screen.Detail.createRoute(it)) }
                                )
                            }
                            composable(Screen.Watchlist.route) {
                                WatchlistScreen(
                                    watchlistRepo = watchlistRepo,
                                    watchedRepo   = watchedRepo,
                                    onMovieClick  = { navController.navigate(Screen.Detail.createRoute(it)) }
                                )
                            }
                            composable(Screen.Watched.route) {
                                WatchedScreen(
                                    watchedRepo  = watchedRepo,
                                    onMovieClick = { navController.navigate(Screen.Detail.createRoute(it)) }
                                )
                            }
                            composable(
                                Screen.Detail.route,
                                arguments = listOf(navArgument("movieId") { type = NavType.IntType })
                            ) { backStack ->
                                val id = backStack.arguments?.getInt("movieId") ?: return@composable
                                DetailScreen(
                                    movieId       = id,
                                    watchlistRepo = watchlistRepo,
                                    watchedRepo   = watchedRepo,
                                    onBack        = { navController.popBackStack() },
                                    onMovieClick  = { navController.navigate(Screen.Detail.createRoute(it)) }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
