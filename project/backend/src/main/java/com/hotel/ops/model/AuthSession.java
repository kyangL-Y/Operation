package com.hotel.ops.model;

public record AuthSession(
    long userId,
    String username,
    String displayName,
    String role
) {}
