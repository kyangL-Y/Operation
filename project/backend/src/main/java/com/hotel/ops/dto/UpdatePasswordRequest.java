package com.hotel.ops.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record UpdatePasswordRequest(
    @NotBlank(message = "旧密码不能为空")
    String oldPassword,

    @NotBlank(message = "新密码不能为空")
    @Size(min = 6, max = 32, message = "新密码长度应在6-32个字符之间")
    String newPassword
) {}
