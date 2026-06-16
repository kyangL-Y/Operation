package com.hotel.ops.dto;

import jakarta.validation.constraints.NotBlank;

public record KnowledgeDocRequest(
    @NotBlank(message = "title 不能为空") String title,
    @NotBlank(message = "content 不能为空") String content
) {}

