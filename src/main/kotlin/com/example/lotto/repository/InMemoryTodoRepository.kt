package com.example.lotto.repository

import com.example.lotto.model.Todo
import org.springframework.stereotype.Repository
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong

@Repository
class InMemoryTodoRepository : TodoRepository {

    private val store = ConcurrentHashMap<Long, Todo>()
    private val sequence = AtomicLong(0)

    override fun nextId(): Long = sequence.incrementAndGet()

    override fun findAll(): List<Todo> =
        store.values.sortedBy { it.id }

    override fun findById(id: Long): Todo? = store[id]

    override fun save(todo: Todo): Todo {
        store[todo.id] = todo
        return todo
    }

    override fun deleteById(id: Long): Boolean =
        store.remove(id) != null
}
