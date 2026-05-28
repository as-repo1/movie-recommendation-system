package com.cinematch.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Purple80   = Color(0xFF8B5CF6)
val PurpleAcc  = Color(0xFFA78BFA)
val Blue80     = Color(0xFF3B82F6)
val Background = Color(0xFF0A0A0F)
val Surface    = Color(0xFF1A1A2E)
val TextPrimary = Color(0xFFE2E8F0)
val TextMuted  = Color(0xFF94A3B8)
val Gold       = Color(0xFFF59E0B)

private val DarkColorScheme = darkColorScheme(
    primary         = Purple80,
    secondary       = Blue80,
    background      = Background,
    surface         = Surface,
    onBackground    = TextPrimary,
    onSurface       = TextPrimary,
    onPrimary       = Color.White,
)

@Composable
fun CineMatchTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        content     = content,
    )
}
