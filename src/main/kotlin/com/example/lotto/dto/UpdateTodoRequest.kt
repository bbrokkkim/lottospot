package com.example.lotto.dto

import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Size

data class UpdateTodoRequest(
    @field:NotBlank(message = "title은 필수입니다")
    @field:Size(max = 200)
    val title: String,
    val description: String? = null,
    val completed: Boolean = false
)
