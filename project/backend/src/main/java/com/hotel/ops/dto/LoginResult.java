package com.hotel.ops.dto;

public record LoginResult(
    String token,
    String username,
    String displayName,
    String role
) {}
