package com.example.lotto.exception

import com.example.lotto.api.store.dto.ApiResponse
import jakarta.validation.ConstraintViolationException
import org.slf4j.LoggerFactory
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.MissingServletRequestParameterException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException

@RestControllerAdvice
class GlobalExceptionHandler {

    private val log = LoggerFactory.getLogger(javaClass)

    /**
     * 파라미터 값이 허용 범위를 벗어난 경우 → 400
     */
    @ExceptionHandler(InvalidParameterException::class)
    fun handleInvalidParameter(ex: InvalidParameterException): ResponseEntity<ApiResponse<Nothing>> {
        log.debug("Invalid parameter: {}", ex.message)
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ApiResponse.error(ex.message ?: "잘못된 요청 파라미터입니다"))
    }

    /**
     * 필수 파라미터 누락 → 400
     */
    @ExceptionHandler(MissingServletRequestParameterException::class)
    fun handleMissingParam(ex: MissingServletRequestParameterException): ResponseEntity<ApiResponse<Nothing>> {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ApiResponse.error("필수 파라미터가 누락되었습니다: ${ex.parameterName}"))
    }

    /**
     * 파라미터 타입 불일치 → 400
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException::class)
    fun handleTypeMismatch(ex: MethodArgumentTypeMismatchException): ResponseEntity<ApiResponse<Nothing>> {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ApiResponse.error("파라미터 타입이 올바르지 않습니다: ${ex.name}"))
    }

    /**
     * Bean Validation (@Valid) 실패 → 400
     */
    @ExceptionHandler(MethodArgumentNotValidException::class)
    fun handleValidation(ex: MethodArgumentNotValidException): ResponseEntity<ApiResponse<Nothing>> {
        val message = ex.bindingResult.fieldErrors
            .joinToString(", ") { "${it.field}: ${it.defaultMessage}" }
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ApiResponse.error(message))
    }

    /**
     * @Validated 제약 위반 → 400
     */
    @ExceptionHandler(ConstraintViolationException::class)
    fun handleConstraintViolation(ex: ConstraintViolationException): ResponseEntity<ApiResponse<Nothing>> {
        val message = ex.constraintViolations.joinToString(", ") { it.message }
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ApiResponse.error(message))
    }

    /**
     * 판매점 없음 → 404
     */
    @ExceptionHandler(StoreNotFoundException::class)
    fun handleStoreNotFound(ex: StoreNotFoundException): ResponseEntity<ApiResponse<Nothing>> {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(ApiResponse.error(ex.message ?: "판매점을 찾을 수 없습니다"))
    }

    /**
     * 그 외 → 500
     */
    @ExceptionHandler(Exception::class)
    fun handleGeneral(ex: Exception): ResponseEntity<ApiResponse<Nothing>> {
        log.error("Unhandled exception", ex)
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ApiResponse.error("서버 오류가 발생했습니다"))
    }
}
