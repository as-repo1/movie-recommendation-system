package com.reclens.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Nord Palette Colors
val NordDarkBg    = Color(0xFF2E3440) // Nord 0
val NordSurface   = Color(0xFF3B4252) // Nord 1
val NordPrimary   = Color(0xFFECEFF4) // Nord 6 (Snow Storm)
val NordMuted     = Color(0xFFD8DEE9) // Nord 4

// Accent colors
val AccentTeal    = Color(0xFF88C0D0) // Nord 8 (Frost)
val AccentBlue    = Color(0xFF81A1C1) // Nord 9 (Frost)
val AccentPurple  = Color(0xFFB48EAD) // Nord 15 (Aurora Purple)
val AccentGreen   = Color(0xFFA3BE8C) // Nord 14 (Aurora Green)
val AccentOrange  = Color(0xFFD08770) // Nord 12 (Aurora Orange)
val AccentRed     = Color(0xFFBF616A) // Nord 11 (Aurora Red)

val Gold          = Color(0xFFEBCB8B) // Nord 13 (Aurora Yellow)
val TextMuted     = NordMuted

@Composable
fun RecLensTheme(
    accent: String = "teal",
    content: @Composable () -> Unit
) {
    val primaryColor = when (accent.lowercase()) {
        "teal"   -> AccentTeal
        "blue"   -> AccentBlue
        "purple" -> AccentPurple
        "green"  -> AccentGreen
        "orange" -> AccentOrange
        "red"    -> AccentRed
        else     -> AccentTeal
    }

    val colorScheme = darkColorScheme(
        primary      = primaryColor,
        secondary    = AccentBlue,
        background   = NordDarkBg,
        surface      = NordSurface,
        onBackground = NordPrimary,
        onSurface    = NordPrimary,
        onPrimary    = NordDarkBg,
        onSecondary  = NordDarkBg,
        error        = AccentRed,
        onError      = NordPrimary
    )

    MaterialTheme(
        colorScheme = colorScheme,
        content     = content
    )
}
