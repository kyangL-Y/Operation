package com.hotel.ops.model;

import java.time.LocalDateTime;

public record AuditLog(
    long id,
    long userId,
    String username,
    String action,
    String module,
    String detail,
    String ipAddress,
    LocalDateTime createdAt
) {}
