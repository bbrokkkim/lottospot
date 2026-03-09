package com.example.lotto.model

import java.time.LocalDateTime

data class Todo(
    val id: Long,
    val title: String,
    val description: String? = null,
    val completed: Boolean = false,
    val createdAt: LocalDateTime = LocalDateTime.now(),
    val updatedAt: LocalDateTime = LocalDateTime.now()
)
