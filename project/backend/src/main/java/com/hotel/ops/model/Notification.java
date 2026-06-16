package com.hotel.ops.model;

import java.time.LocalDateTime;

public record Notification(
    long id,
    long userId,
    String title,
    String content,
    String type,
    boolean isRead,
    LocalDateTime createdAt
) {}
