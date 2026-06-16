package com.hotel.ops.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record UserCreateRequest(
    @NotBlank(message = "displayName 不能为空") String displayName,
    @NotBlank(message = "username 不能为空")
    @Size(min = 3, max = 24, message = "username 长度需在 3 到 24 之间")
    String username,
    @NotBlank(message = "password 不能为空")
    @Size(min = 6, max = 32, message = "password 长度需在 6 到 32 之间")
    String password,
    @NotBlank(message = "role 不能为空") String role
) {}
