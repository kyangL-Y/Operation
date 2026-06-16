package com.hotel.ops.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record UpdateProfileRequest(
    @NotBlank(message = "显示名称不能为空")
    @Size(min = 2, max = 32, message = "显示名称长度应在2-32个字符之间")
    String displayName
) {}
