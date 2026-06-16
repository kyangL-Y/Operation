package com.hotel.ops.dto;

import java.util.List;

public record RagAskResult(
    String answer,
    List<String> citations,
    List<String> suggestions,
    List<String> queryPlan,
    String searchDepth,
    String confidence,
    String mode,
    String retrievalMode,
    String generationMode,
    String source
) {}

