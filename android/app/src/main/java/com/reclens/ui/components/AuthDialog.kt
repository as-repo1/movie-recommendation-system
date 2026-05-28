package com.reclens.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.reclens.data.api.AuthRequest
import com.reclens.data.api.RetrofitClient
import com.reclens.data.repository.SettingsRepository
import com.reclens.data.repository.WatchlistRepository
import com.reclens.data.repository.WatchedRepository
import kotlinx.coroutines.launch

@Composable
fun AuthDialog(
    onDismiss: () -> Unit,
    onSuccess: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    
    val settingsRepo = remember { SettingsRepository(context) }
    val watchlistRepo = remember { WatchlistRepository(context) }
    val watchedRepo = remember { WatchedRepository(context) }

    var isLoginTab by remember { mutableStateOf(true) }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = { if (!loading) onDismiss() },
        title = {
            Text(if (isLoginTab) "Sign In to RecLens" else "Create RecLens Account")
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Tab Selection Row
                TabRow(selectedTabIndex = if (isLoginTab) 0 else 1) {
                    Tab(
                        selected = isLoginTab,
                        onClick = { isLoginTab = true; errorMessage = null },
                        text = { Text("Sign In") }
                    )
                    Tab(
                        selected = !isLoginTab,
                        onClick = { isLoginTab = false; errorMessage = null },
                        text = { Text("Sign Up") }
                    )
                }

                Spacer(modifier = Modifier.height(4.dp))

                OutlinedTextField(
                    value = username,
                    onValueChange = { username = it },
                    label = { Text("Username") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !loading
                )

                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("Password") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !loading
                )

                errorMessage?.let { error ->
                    Text(
                        text = error,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(horizontal = 4.dp)
                    )
                }

                if (loading) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(32.dp))
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (username.isBlank() || password.isBlank()) {
                        errorMessage = "Please fill in all fields"
                        return@Button
                    }
                    loading = true
                    errorMessage = null
                    
                    scope.launch {
                        try {
                            val api = RetrofitClient.getApi(context)
                            val anonId = settingsRepo.getSessionId()
                            val body = AuthRequest(username, password, anonId)
                            
                            val response = if (isLoginTab) {
                                api.login(body)
                            } else {
                                api.register(body)
                            }

                            // Save credentials
                            settingsRepo.setAuthToken(response.accessToken)
                            settingsRepo.setUsername(response.user.username)

                            // Sync backend watchlist & watched items immediately
                            watchlistRepo.syncWithBackend()
                            watchedRepo.syncWithBackend()

                            loading = false
                            onSuccess()
                            onDismiss()
                        } catch (e: Exception) {
                            errorMessage = e.message ?: "Authentication failed. Check your network or credentials."
                            loading = false
                        }
                    }
                },
                enabled = !loading
            ) {
                Text(if (isLoginTab) "Sign In" else "Sign Up")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                enabled = !loading
            ) {
                Text("Cancel")
            }
        }
    )
}
