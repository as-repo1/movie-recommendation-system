package com.cinematch

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import com.cinematch.data.repository.WatchlistRepository
import com.cinematch.data.repository.WatchedRepository
import com.cinematch.ui.home.HomeScreen
import com.cinematch.ui.search.SearchScreen
import com.cinematch.ui.theme.CineMatchTheme
import com.cinematch.ui.watchlist.WatchlistScreen
import com.cinematch.ui.watched.WatchedScreen
import com.cinematch.ui.detail.DetailScreen

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
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val watchlistRepo = WatchlistRepository(this)
        val watchedRepo   = WatchedRepository(this)

        setContent {
            CineMatchTheme {
                val navController = rememberNavController()
                val currentBackStack by navController.currentBackStackEntryAsState()
                val currentRoute = currentBackStack?.destination?.route

                val bottomTabs = listOf(Screen.Home, Screen.Search, Screen.Watchlist, Screen.Watched)

                Scaffold(
                    modifier = Modifier.fillMaxSize(),
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
