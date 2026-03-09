package com.example.lotto.dto

import com.example.lotto.model.Todo
import java.time.LocalDateTime

data class TodoResponse(
    val id: Long,
    val title: String,
    val description: String?,
    val completed: Boolean,
    val createdAt: LocalDateTime,
    val updatedAt: LocalDateTime
) {
    companion object {
        fun from(todo: Todo) = TodoResponse(
            id = todo.id,
            title = todo.title,
            description = todo.description,
            completed = todo.completed,
            createdAt = todo.createdAt,
            updatedAt = todo.updatedAt
        )
    }
}
