package com.example.lotto.exception

/**
 * 요청 파라미터가 허용 범위를 벗어났을 때 던지는 예외.
 * GlobalExceptionHandler 에서 HTTP 400 으로 변환된다.
 */
class InvalidParameterException(message: String) : RuntimeException(message)
