package com.example.lotto.exception

/**
 * 판매점을 찾을 수 없을 때 던지는 예외.
 * GlobalExceptionHandler 에서 HTTP 404 로 변환된다.
 */
class StoreNotFoundException(storeId: Long) : RuntimeException("판매점을 찾을 수 없습니다. id=$storeId")
