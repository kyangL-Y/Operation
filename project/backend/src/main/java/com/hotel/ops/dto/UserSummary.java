package com.hotel.ops.dto;

import java.time.LocalDateTime;

public record UserSummary(
    long id,
    String username,
    String displayName,
    String role,
    String status,
    LocalDateTime createdAt
) {}
