package com.hotel.ops.dto;

import jakarta.validation.constraints.NotBlank;

public record RagAskRequest(
    @NotBlank(message = "question 不能为空") String question
) {}

