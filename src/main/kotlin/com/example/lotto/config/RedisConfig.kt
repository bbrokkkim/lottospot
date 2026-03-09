package com.example.lotto.config

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.SerializationFeature
import com.fasterxml.jackson.module.kotlin.kotlinModule
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.data.redis.connection.RedisConnectionFactory
import org.springframework.data.redis.core.RedisTemplate
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer
import org.springframework.data.redis.serializer.StringRedisSerializer

/**
 * Redis 직렬화 설정.
 *
 * 키는 String, 값은 JSON(Jackson) 으로 직렬화한다.
 * ObjectMapper.findAndRegisterModules() 로 JavaTimeModule 을 자동 등록하여
 * LocalDate / LocalDateTime 을 ISO-8601 문자열로 직렬화한다.
 */
@Configuration
class RedisConfig {

    @Bean
    fun redisObjectMapper(): ObjectMapper =
        ObjectMapper()
            .registerModule(kotlinModule())
            .findAndRegisterModules()
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)

    @Bean
    fun redisTemplate(
        connectionFactory: RedisConnectionFactory,
        redisObjectMapper: ObjectMapper
    ): RedisTemplate<String, Any> {
        val valueSerializer = Jackson2JsonRedisSerializer(redisObjectMapper, Any::class.java)

        val template = RedisTemplate<String, Any>()
        template.connectionFactory = connectionFactory
        template.keySerializer = StringRedisSerializer()
        template.valueSerializer = valueSerializer
        template.hashKeySerializer = StringRedisSerializer()
        template.hashValueSerializer = valueSerializer
        return template
    }
}
