package com.example.lotto.api.store.dto

/**
 * 모든 API 응답에 공통으로 사용되는 표준 래퍼.
 *
 * success = true  → 정상 응답, data 에 결과 포함
 * success = false → 에러 응답, message 에 사유 포함
 */
data class ApiResponse<T>(
    val success: Boolean,
    val message: String,
    val data: T? = null
) {
    companion object {
        fun <T> ok(data: T, message: String = "OK"): ApiResponse<T> =
            ApiResponse(success = true, message = message, data = data)

        fun <T> error(message: String, status: Int? = null): ApiResponse<T> =
            ApiResponse(success = false, message = message, data = null)
    }
}
