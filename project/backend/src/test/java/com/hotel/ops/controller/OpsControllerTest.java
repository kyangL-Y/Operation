package com.hotel.ops.controller;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.dto.RagAskResult;
import com.hotel.ops.service.MlServiceClient;
import com.hotel.ops.service.RagService;
import java.sql.Date;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.jdbc.core.JdbcTemplate;

class OpsControllerTest {

  @Test
  void decisionSupportShouldReturnPayloadWhenMlResponseMissesFields() {
    MlServiceClient mlClient = mock(MlServiceClient.class);
    RagService ragService = mock(RagService.class);
    @SuppressWarnings("unchecked")
    ObjectProvider<JdbcTemplate> jdbcProvider = mock(ObjectProvider.class);

    when(jdbcProvider.getIfAvailable()).thenReturn(null);
    when(mlClient.isAvailable()).thenReturn(true);
    when(mlClient.occupancyPredict(anyMap())).thenReturn(new HashMap<>());
    when(mlClient.revenuePredict(anyMap())).thenReturn(null);
    when(mlClient.cancellationPredict(anyMap())).thenReturn(new HashMap<>());
    when(mlClient.decisionAnalyze(anyMap())).thenReturn(null);
    when(ragService.ask(anyString())).thenReturn(new RagAskResult(
        null,
        List.of(),
        List.of(),
        List.of(),
        "low",
        "低",
        "standard",
        "keyword_fallback",
        "template_fallback",
        "java-local-fallback"
    ));

    OpsController controller = new OpsController(mlClient, ragService, jdbcProvider, false);
    ApiResponse<Map<String, Object>> response = controller.decisionSupport();

    assertEquals(0, response.code());
    assertNotNull(response.data());
    assertEquals(true, response.data().get("mlEnabled"));

    @SuppressWarnings("unchecked")
    Map<String, Object> forecast = (Map<String, Object>) response.data().get("forecast");
    assertNotNull(forecast);
    assertNotNull(forecast.get("nextDayOccupancy"));
    assertNotNull(forecast.get("nextDayRevenue"));
    assertNotNull(forecast.get("nextDayCancellationRate"));

    @SuppressWarnings("unchecked")
    Map<String, Object> decision = (Map<String, Object>) response.data().get("decision");
    assertNotNull(decision);
    assertEquals("stable", decision.get("riskLevel"));
    assertNotNull(decision.get("summary"));

    @SuppressWarnings("unchecked")
    List<String> rootCauses = (List<String>) decision.get("rootCauses");
    assertFalse(rootCauses.isEmpty());
    assertTrue(rootCauses.get(0).contains("核心指标"));

    @SuppressWarnings("unchecked")
    List<String> actions = (List<String>) decision.get("recommendedActions");
    assertFalse(actions.isEmpty());
  }

  @Test
  void dashboardShouldPreferJdbcMetricsWhenJdbcIsEnabled() {
    MlServiceClient mlClient = mock(MlServiceClient.class);
    RagService ragService = mock(RagService.class);
    JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
    @SuppressWarnings("unchecked")
    ObjectProvider<JdbcTemplate> jdbcProvider = mock(ObjectProvider.class);

    when(jdbcProvider.getIfAvailable()).thenReturn(jdbcTemplate);
    when(jdbcTemplate.queryForObject(anyString(), org.mockito.ArgumentMatchers.eq(Integer.class))).thenReturn(1, 7);
    when(jdbcTemplate.queryForList(anyString())).thenReturn(List.of(
        row(LocalDate.parse("2026-02-23"), 0.83, 131000, 0.15, 4.52, 0.05),
        row(LocalDate.parse("2026-02-22"), 0.80, 124000, 0.16, 4.48, 0.07),
        row(LocalDate.parse("2026-02-21"), 0.82, 128000, 0.15, 4.50, 0.06),
        row(LocalDate.parse("2026-02-20"), 0.81, 119000, 0.16, 4.42, 0.06),
        row(LocalDate.parse("2026-02-19"), 0.79, 112000, 0.17, 4.35, 0.07),
        row(LocalDate.parse("2026-02-18"), 0.76, 108000, 0.18, 4.33, 0.07),
        row(LocalDate.parse("2026-02-17"), 0.74, 102000, 0.19, 4.30, 0.08)
    ));

    OpsController controller = new OpsController(mlClient, ragService, jdbcProvider, true);
    ApiResponse<Map<String, Object>> response = controller.dashboard();

    assertEquals(0, response.code());
    assertNotNull(response.data());
    assertEquals(0.83, ((Number) response.data().get("occupancyRate")).doubleValue(), 0.0001);
    assertEquals(131000, ((Number) response.data().get("dailyRevenue")).intValue());
    assertEquals(List.of("02-17", "02-18", "02-19", "02-20", "02-21", "02-22", "02-23"), response.data().get("dates"));
  }

  private Map<String, Object> row(
      LocalDate bizDate,
      double occupancyRate,
      int revenue,
      double cancellationRate,
      double reviewScore,
      double negativeRate
  ) {
    Map<String, Object> row = new HashMap<>();
    row.put("biz_date", Date.valueOf(bizDate));
    row.put("occupancy_rate", occupancyRate);
    row.put("revenue", revenue);
    row.put("cancellation_rate", cancellationRate);
    row.put("review_score", reviewScore);
    row.put("negative_rate", negativeRate);
    return row;
  }
}
