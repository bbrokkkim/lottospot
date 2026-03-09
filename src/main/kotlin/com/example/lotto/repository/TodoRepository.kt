package com.example.lotto.repository

import com.example.lotto.model.Todo

interface TodoRepository {
    fun findAll(): List<Todo>
    fun findById(id: Long): Todo?
    fun save(todo: Todo): Todo
    fun deleteById(id: Long): Boolean
    fun nextId(): Long
}
