package com.example.lotto.exception

class TodoNotFoundException(id: Long) :
    RuntimeException("Todo를 찾을 수 없습니다. id=$id")
