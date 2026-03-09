package com.example.lotto.service

import com.example.lotto.dto.CreateTodoRequest
import com.example.lotto.dto.UpdateTodoRequest
import com.example.lotto.exception.TodoNotFoundException
import com.example.lotto.model.Todo
import com.example.lotto.repository.TodoRepository
import org.springframework.stereotype.Service
import java.time.LocalDateTime

@Service
class TodoService(private val todoRepository: TodoRepository) {

    fun findAll(): List<Todo> = todoRepository.findAll()

    fun findById(id: Long): Todo =
        todoRepository.findById(id) ?: throw TodoNotFoundException(id)

    fun create(request: CreateTodoRequest): Todo {
        val todo = Todo(
            id = todoRepository.nextId(),
            title = request.title,
            description = request.description
        )
        return todoRepository.save(todo)
    }

    fun update(id: Long, request: UpdateTodoRequest): Todo {
        val existing = findById(id)
        val updated = existing.copy(
            title = request.title,
            description = request.description,
            completed = request.completed,
            updatedAt = LocalDateTime.now()
        )
        return todoRepository.save(updated)
    }

    fun toggleComplete(id: Long): Todo {
        val existing = findById(id)
        val updated = existing.copy(
            completed = !existing.completed,
            updatedAt = LocalDateTime.now()
        )
        return todoRepository.save(updated)
    }

    fun delete(id: Long) {
        findById(id)
        todoRepository.deleteById(id)
    }
}
