package com.hotel.ops.dto;

import java.math.BigDecimal;

public record OpsMetricRequest(
    String bizDate,
    BigDecimal occupancyRate,
    BigDecimal revenue,
    BigDecimal cancellationRate,
    BigDecimal reviewScore,
    BigDecimal negativeRate
) {}
