package com.hotel.ops.model;

import java.time.LocalDateTime;

public record SystemConfig(
    String configKey,
    String configValue,
    String description,
    LocalDateTime updatedAt
) {}
