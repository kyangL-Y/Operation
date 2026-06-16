package com.hotel.ops.model;

import java.time.LocalDateTime;

public record KnowledgeDoc(
    long id,
    String title,
    String content,
    LocalDateTime createdAt
) {}

