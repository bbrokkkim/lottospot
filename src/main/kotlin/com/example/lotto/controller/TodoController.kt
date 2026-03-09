package com.example.lotto.controller

import com.example.lotto.dto.CreateTodoRequest
import com.example.lotto.dto.TodoResponse
import com.example.lotto.dto.UpdateTodoRequest
import com.example.lotto.service.TodoService
import jakarta.validation.Valid
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/todos")
class TodoController(private val todoService: TodoService) {

    @GetMapping
    fun findAll(): ResponseEntity<List<TodoResponse>> =
        ResponseEntity.ok(todoService.findAll().map { TodoResponse.from(it) })

    @GetMapping("/{id}")
    fun findById(@PathVariable id: Long): ResponseEntity<TodoResponse> =
        ResponseEntity.ok(TodoResponse.from(todoService.findById(id)))

    @PostMapping
    fun create(@Valid @RequestBody request: CreateTodoRequest): ResponseEntity<TodoResponse> =
        ResponseEntity.status(HttpStatus.CREATED)
            .body(TodoResponse.from(todoService.create(request)))

    @PutMapping("/{id}")
    fun update(
        @PathVariable id: Long,
        @Valid @RequestBody request: UpdateTodoRequest
    ): ResponseEntity<TodoResponse> =
        ResponseEntity.ok(TodoResponse.from(todoService.update(id, request)))

    @PatchMapping("/{id}/complete")
    fun toggleComplete(@PathVariable id: Long): ResponseEntity<TodoResponse> =
        ResponseEntity.ok(TodoResponse.from(todoService.toggleComplete(id)))

    @DeleteMapping("/{id}")
    fun delete(@PathVariable id: Long): ResponseEntity<Unit> {
        todoService.delete(id)
        return ResponseEntity.noContent().build()
    }
}
