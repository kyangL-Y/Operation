package com.hotel.ops.dto;

import jakarta.validation.constraints.NotBlank;

public record UserRoleUpdateRequest(
    @NotBlank(message = "role 不能为空") String role
) {}
