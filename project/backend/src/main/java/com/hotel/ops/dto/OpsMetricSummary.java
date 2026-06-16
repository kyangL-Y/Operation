package com.hotel.ops.dto;

import java.math.BigDecimal;

public record OpsMetricSummary(
    long id,
    String bizDate,
    BigDecimal occupancyRate,
    BigDecimal revenue,
    BigDecimal cancellationRate,
    BigDecimal reviewScore,
    BigDecimal negativeRate
) {}
