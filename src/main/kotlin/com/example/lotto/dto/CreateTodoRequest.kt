package com.example.lotto.dto

import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Size

data class CreateTodoRequest(
    @field:NotBlank(message = "title은 필수입니다")
    @field:Size(max = 200, message = "title은 200자 이하여야 합니다")
    val title: String,
    val description: String? = null
)
