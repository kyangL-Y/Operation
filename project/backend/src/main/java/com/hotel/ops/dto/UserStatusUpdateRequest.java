package com.hotel.ops.dto;

import jakarta.validation.constraints.NotBlank;

public record UserStatusUpdateRequest(
    @NotBlank(message = "status 不能为空") String status
) {}
