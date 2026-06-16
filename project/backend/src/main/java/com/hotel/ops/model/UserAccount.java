package com.hotel.ops.model;

import java.time.LocalDateTime;

public record UserAccount(
    long id,
    String username,
    String displayName,
    String role,
    String status,
    LocalDateTime createdAt
) {}
