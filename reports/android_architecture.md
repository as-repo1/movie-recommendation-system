# RecLens Mobile — Android Native Client Architecture

This document describes the design, architecture, implementation, and compilation workflow of the **RecLens Mobile** native Android application.

---

## 1. Architectural Overview

RecLens Mobile is written in **Kotlin** and built on a modern Android architecture featuring **Jetpack Compose** for the UI, **Retrofit2** for networking, and **ViewModels** with **StateFlow** for state management. It maps directly to the web client's features while optimizing for mobile-first user interaction.

```
                     ┌──────────────────────────────────────┐
                     │            User Interface            │
                     │          (Jetpack Compose)           │
                     └──────────────────┬───────────────────┘
                                        │ (Observe StateFlow)
                                        ▼
                     ┌──────────────────────────────────────┐
                     │            ViewModels                │
                     │  (HomeScreen, SearchScreen, etc.)    │
                     └──────────────────┬───────────────────┘
                                        │ (Repository Calls)
                                        ▼
                     ┌──────────────────────────────────────┐
                     │            Repositories              │
                     │   (WatchlistRepo, WatchedRepo)       │
                     └─────────┬──────────────────┬─────────┘
                               │                  │
                               ▼                  ▼
                     ┌──────────────────┐ ┌─────────────────┐
                     │   Retrofit API   │ │SharedPreferences│
                     │ (Remote Backend) │ │  (Local Cache)  │
                     └──────────────────┘ └─────────────────┘
```

---

## 2. Core Modules & Data Models

### 2.1 The Movie Data Model
The Android client maps JSON payloads from the RecLens backend into Kotlin data classes using Gson annotations for proper field serialization:

```kotlin
data class Movie(
    val id: Int,
    val title: String,
    val overview: String = "",
    @SerializedName("poster_url") val posterUrl: String = "",
    @SerializedName("backdrop_url") val backdropUrl: String = "",
    val genres: List<String> = emptyList(),
    val year: Int? = null,
    @SerializedName("vote_average") val voteAverage: Double = 0.0,
    @SerializedName("vote_count") val voteCount: Int = 0,
    val runtime: Int? = null,
    @SerializedName("imdb_id") val imdbId: String = ""
)
```

---

## 3. UI Layer & Jetpack Compose Screens

The interface implements a responsive, dark-themed styling aligned with the RecLens brand guidelines (Slate/Nord backgrounds, Purple/Blue highlights, and rounded card styling).

### 3.1 Main Activity Navigation Drawer (`MainActivity.kt`)
The entry point orchestrates global routing via a customized side **Navigation Drawer** and bottom navigation:
- **Server URL Control**: Allows users to dynamically change the API target server directly from the UI (defaulting to emulator loopback `http://10.0.2.2:8000`).
- **Ping Diagnostic Utility**: Triggers network request latency pings directly to the configured endpoint to verify connection state.
- **Theme Engine Toggle**: Dynamically alters UI highlighting configurations.
- **Session Sync**: Integrated with authentication controls (Login/Register buttons inside the drawer header) to automatically migrate anonymous sessions.

### 3.2 Screens
- **HomeScreen (`HomeScreen.kt`)**: Displays movie carousels. Rather than using nested vertical grids which cut off on smaller screens, it leverages horizontal `LazyRow` carousels for *"For You"* and *"Trending"* lists, enabling an immersive user flow.
- **SearchScreen (`SearchScreen.kt`)**: Implements an instant-search search bar triggering debounced requests to the search endpoint.
- **DetailScreen (`DetailScreen.kt`)**: Renders high-resolution backdrop banners, title headers, and metadata chips. Similar movie recommendations are rendered dynamically inside a standard scrollable column rather than nested scrollable elements to prevent layout cutoff issues.
- **Watchlist & Watched Screens (`WatchlistScreen.kt`, `WatchedScreen.kt`)**: Dual columns grid displays. Supported by `SharedPreferences` state. The Watched screen supports sorting list items by *Date Added* or *My Rating* and deleting entries.

---

## 4. Repositories & State Synchronization

The client maintains offline-first responsive behavior using SharedPreferences caching. 

### 4.1 Sync Flow
1. When a user interacts with the app anonymously, action records are keyed to an `anonymous_session_id`.
2. When the user logs in, the `AuthDialog` triggers authentication, receives a JWT, and sends the `anonymous_session_id` to the backend.
3. The backend runs an atomic SQL update transferring all tracking history to the permanent account ID.
4. The local caches are invalidated and re-fetched from `/api/watchlist` and `/api/watched` to sync state cleanly.

---

## 5. Build Configurations & AAPT2 Workarounds

### 5.1 Gradle Realignment
The workspace realigned Android compilation via the following configurations:
- `local.properties`: Defines the local SDK path explicitly, resolving permissions conflicts:
  ```properties
  sdk.dir=/home/chaos/Android/Sdk
  ```
- `build.gradle.kts` (App level): Configured package namespace and Application ID mapping:
  ```kotlin
  android {
      namespace = "com.reclens"
      defaultConfig {
          applicationId = "com.reclens"
      }
  }
  ```

### 5.2 AAPT2 PNG Crunching Fix
AI-generated PNG launcher icons contain embedded metadata blocks (like iCCP or custom headers) that cause the AAPT2 resource parser to fail with crunching exceptions. We resolved this build block by running:
```bash
convert icon-raw.png -strip android/app/src/main/res/drawable/ic_launcher.png
```
This strips extraneous non-color profile metadata, enabling clean releases compile via `./gradlew assembleRelease`.
