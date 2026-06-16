package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.dto.OpsMetricRequest;
import com.hotel.ops.dto.OpsMetricSummary;
import com.hotel.ops.dto.RagAskResult;
import com.hotel.ops.service.MlServiceClient;
import com.hotel.ops.service.RagService;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.math.BigDecimal;
import java.sql.Date;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.temporal.IsoFields;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/ops")
public class OpsController {

  private static final Logger log = LoggerFactory.getLogger(OpsController.class);
  private static final int TOTAL_ROOMS = 120;

  private static final String CSV_PATH = System.getProperty("user.dir")
      + File.separator + ".." + File.separator + "ml" + File.separator + "data"
      + File.separator + "hotel_ops_1095.csv";

  private static final String CREATE_METRIC_TABLE_SQL = """
      CREATE TABLE IF NOT EXISTS ops_daily_metric (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        biz_date DATE NOT NULL,
        occupancy_rate DECIMAL(5, 4) NOT NULL,
        revenue DECIMAL(12, 2) NOT NULL,
        cancellation_rate DECIMAL(5, 4) NOT NULL DEFAULT 0.1600,
        review_score DECIMAL(3, 2) NOT NULL,
        negative_rate DECIMAL(5, 4) NOT NULL,
        UNIQUE KEY uk_biz_date (biz_date)
      )
      """;

  private static final String HAS_CANCELLATION_RATE_COLUMN_SQL = """
      SELECT COUNT(1)
      FROM INFORMATION_SCHEMA.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'ops_daily_metric'
        AND COLUMN_NAME = 'cancellation_rate'
      """;

  private static final String ALTER_METRIC_TABLE_SQL = """
      ALTER TABLE ops_daily_metric
      ADD COLUMN cancellation_rate DECIMAL(5, 4) NOT NULL DEFAULT 0.1600
      """;

  private static final String COUNT_METRIC_SQL = "SELECT COUNT(1) FROM ops_daily_metric";

  private static final String INSERT_METRIC_SQL = """
      INSERT INTO ops_daily_metric
      (biz_date, occupancy_rate, revenue, cancellation_rate, review_score, negative_rate)
      VALUES (?, ?, ?, ?, ?, ?)
      ON DUPLICATE KEY UPDATE
      occupancy_rate = VALUES(occupancy_rate),
      revenue = VALUES(revenue),
      cancellation_rate = VALUES(cancellation_rate),
      review_score = VALUES(review_score),
      negative_rate = VALUES(negative_rate)
      """;

  private static final String SELECT_LAST7_METRIC_SQL = """
      SELECT biz_date, occupancy_rate, revenue, cancellation_rate, review_score, negative_rate
      FROM ops_daily_metric
      ORDER BY biz_date DESC
      LIMIT 7
      """;

  private final MlServiceClient mlClient;
  private final RagService ragService;
  private final JdbcTemplate jdbcTemplate;
  private volatile boolean jdbcEnabled = true;

  public OpsController(
      MlServiceClient mlClient,
      RagService ragService,
      ObjectProvider<JdbcTemplate> jdbcTemplateProvider,
      @Value("${hotel.jdbc.enabled:false}") boolean jdbcFeatureEnabled
  ) {
    this.mlClient = mlClient;
    this.ragService = ragService;
    this.jdbcTemplate = jdbcFeatureEnabled ? jdbcTemplateProvider.getIfAvailable() : null;
    bootstrapJdbcMetrics();
  }

  @GetMapping("/dashboard")
  public ApiResponse<Map<String, Object>> dashboard() {
    return ApiResponse.ok(buildDashboardData());
  }

  @GetMapping("/metrics")
  public ApiResponse<List<OpsMetricSummary>> listMetrics(
      @RequestParam(required = false) String startDate,
      @RequestParam(required = false) String endDate) {
    if (useJdbc()) {
      try {
        StringBuilder sql = new StringBuilder(
            "SELECT id, biz_date, occupancy_rate, revenue, cancellation_rate, review_score, negative_rate FROM ops_daily_metric WHERE 1=1");
        List<Object> params = new ArrayList<>();
        if (startDate != null && !startDate.isBlank()) {
          sql.append(" AND biz_date >= ?");
          params.add(Date.valueOf(LocalDate.parse(startDate)));
        }
        if (endDate != null && !endDate.isBlank()) {
          sql.append(" AND biz_date <= ?");
          params.add(Date.valueOf(LocalDate.parse(endDate)));
        }
        sql.append(" ORDER BY biz_date DESC LIMIT 90");
        List<OpsMetricSummary> result = jdbcTemplate.query(sql.toString(), (rs, i) ->
            new OpsMetricSummary(
                rs.getLong("id"),
                rs.getDate("biz_date").toLocalDate().toString(),
                rs.getBigDecimal("occupancy_rate"),
                rs.getBigDecimal("revenue"),
                rs.getBigDecimal("cancellation_rate"),
                rs.getBigDecimal("review_score"),
                rs.getBigDecimal("negative_rate")
            ), params.toArray());
        return ApiResponse.ok(result);
      } catch (DataAccessException ex) {
        log.warn("查询运营指标失败: {}", ex.getMessage());
      }
    }
    return ApiResponse.ok(buildStaticMetrics());
  }

  @PostMapping("/metrics")
  public ApiResponse<OpsMetricSummary> createMetric(@RequestBody OpsMetricRequest req) {
    if (useJdbc()) {
      try {
        String sql = "INSERT INTO ops_daily_metric (biz_date, occupancy_rate, revenue, cancellation_rate, review_score, negative_rate) VALUES (?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE occupancy_rate=VALUES(occupancy_rate), revenue=VALUES(revenue), cancellation_rate=VALUES(cancellation_rate), review_score=VALUES(review_score), negative_rate=VALUES(negative_rate)";
        jdbcTemplate.update(sql,
            Date.valueOf(LocalDate.parse(req.bizDate())),
            req.occupancyRate(), req.revenue(), req.cancellationRate(),
            req.reviewScore(), req.negativeRate());
        return ApiResponse.ok(new OpsMetricSummary(0, req.bizDate(), req.occupancyRate(),
            req.revenue(), req.cancellationRate(), req.reviewScore(), req.negativeRate()));
      } catch (DataAccessException ex) {
        log.warn("新增运营指标失败: {}", ex.getMessage());
      }
    }
    return ApiResponse.ok(new OpsMetricSummary(System.currentTimeMillis(), req.bizDate(),
        req.occupancyRate(), req.revenue(), req.cancellationRate(), req.reviewScore(), req.negativeRate()));
  }

  @PutMapping("/metrics/{id}")
  public ApiResponse<OpsMetricSummary> updateMetric(@PathVariable long id, @RequestBody OpsMetricRequest req) {
    if (useJdbc()) {
      try {
        String sql = "UPDATE ops_daily_metric SET biz_date=?, occupancy_rate=?, revenue=?, cancellation_rate=?, review_score=?, negative_rate=? WHERE id=?";
        jdbcTemplate.update(sql,
            Date.valueOf(LocalDate.parse(req.bizDate())),
            req.occupancyRate(), req.revenue(), req.cancellationRate(),
            req.reviewScore(), req.negativeRate(), id);
      } catch (DataAccessException ex) {
        log.warn("更新运营指标失败: {}", ex.getMessage());
      }
    }
    return ApiResponse.ok(new OpsMetricSummary(id, req.bizDate(), req.occupancyRate(),
        req.revenue(), req.cancellationRate(), req.reviewScore(), req.negativeRate()));
  }

  @DeleteMapping("/metrics/{id}")
  public ApiResponse<Void> deleteMetric(@PathVariable long id) {
    if (useJdbc()) {
      try {
        jdbcTemplate.update("DELETE FROM ops_daily_metric WHERE id=?", id);
      } catch (DataAccessException ex) {
        log.warn("删除运营指标失败: {}", ex.getMessage());
      }
    }
    return ApiResponse.ok(null);
  }

  private List<OpsMetricSummary> buildStaticMetrics() {
    List<OpsMetricSummary> list = new ArrayList<>();
    list.add(new OpsMetricSummary(1, "2026-03-25", BigDecimal.valueOf(0.82), BigDecimal.valueOf(58000), BigDecimal.valueOf(0.06), BigDecimal.valueOf(4.6), BigDecimal.valueOf(0.04)));
    list.add(new OpsMetricSummary(2, "2026-03-24", BigDecimal.valueOf(0.78), BigDecimal.valueOf(52000), BigDecimal.valueOf(0.08), BigDecimal.valueOf(4.5), BigDecimal.valueOf(0.05)));
    list.add(new OpsMetricSummary(3, "2026-03-23", BigDecimal.valueOf(0.85), BigDecimal.valueOf(62000), BigDecimal.valueOf(0.05), BigDecimal.valueOf(4.7), BigDecimal.valueOf(0.03)));
    list.add(new OpsMetricSummary(4, "2026-03-22", BigDecimal.valueOf(0.72), BigDecimal.valueOf(48000), BigDecimal.valueOf(0.10), BigDecimal.valueOf(4.3), BigDecimal.valueOf(0.08)));
    list.add(new OpsMetricSummary(5, "2026-03-21", BigDecimal.valueOf(0.68), BigDecimal.valueOf(45000), BigDecimal.valueOf(0.12), BigDecimal.valueOf(4.2), BigDecimal.valueOf(0.09)));
    return list;
  }

  @GetMapping("/decision-support")
  public ApiResponse<Map<String, Object>> decisionSupport() {
    Map<String, Object> dashboard = buildDashboardData();
    Map<String, Object> features = buildForecastFeatures(dashboard);

    if (!mlClient.isAvailable()) {
      return ApiResponse.ok(Map.of(
          "mlEnabled", false,
          "message", "预测服务暂未连接，当前仅提供基础看板与资料问答。",
          "forecast", Map.of(),
          "decision", Map.of(
              "riskLevel", "unavailable",
              "summary", "预测与决策分析暂未连接，请先启动预测服务。",
              "rootCauses", List.of("当前未连接运营预测服务。"),
              "recommendedActions", List.of("先启动预测服务，再查看预测与决策建议。")
          ),
          "knowledgeAdvice", "",
          "citations", List.of()
      ));
    }

    Map<String, Object> occResult = safeMap(mlClient.occupancyPredict(features));
    Map<String, Object> revenueResult = safeMap(mlClient.revenuePredict(features));
    Map<String, Object> cancellationResult = safeMap(mlClient.cancellationPredict(features));
    Map<String, Object> metrics = buildDecisionMetrics(
        dashboard, occResult, revenueResult, cancellationResult, features
    );
    Map<String, Object> decision = safeMap(mlClient.decisionAnalyze(metrics));

    String ragQuestion = "酒店运营决策支持：" + decision.get("summary")
        + "。请结合知识库给出处理建议，重点覆盖投诉处理、前台响应、排班和换房预案。";
    RagAskResult ragResult = ragService.ask(ragQuestion);
    List<String> ragCitations = ragResult != null && ragResult.citations() != null
        ? ragResult.citations()
        : List.of();

    Map<String, Object> forecast = new HashMap<>();
    int availableRooms = toInteger(dashboard.get("availableRooms"), TOTAL_ROOMS);
    double nextDayOccupancy = toDouble(
        occResult.get("predicted_occupancy"),
        toDouble(dashboard.get("occupancyRate"), 0.0)
    );
    forecast.put(
        "nextDayOccupancy",
        nextDayOccupancy
    );
    forecast.put("availableRooms", availableRooms);
    forecast.put("nextDayOccupiedRooms", (int) Math.round(nextDayOccupancy * availableRooms));
    forecast.put(
        "nextDayRevenue",
        (int) Math.round(toDouble(revenueResult.get("predicted_revenue"), toDouble(dashboard.get("dailyRevenue"), 0.0)))
    );
    forecast.put(
        "nextDayCancellationRate",
        toDouble(
            cancellationResult.get("predicted_cancellation_rate"),
            toDouble(dashboard.get("cancellationRate"), 0.0)
        )
    );

    Map<String, Object> decisionData = new HashMap<>();
    decisionData.put("riskLevel", toNonBlankString(decision.get("risk_level"), "stable"));
    decisionData.put("summary", toNonBlankString(decision.get("summary"), "决策分析已生成，请结合运营经验执行。"));
    decisionData.put("rootCauses", toStringList(decision.get("root_causes"), "核心指标整体平稳，暂无明显经营异常。"));
    decisionData.put("recommendedActions", toStringList(decision.get("recommended_actions"), "维持当前排班与房价策略，持续观察评分和差评率变化。"));

    Map<String, Object> payload = new HashMap<>();
    payload.put("mlEnabled", true);
    payload.put("forecast", forecast);
    payload.put("decision", decisionData);
    payload.put("knowledgeAdvice", toNonBlankString(ragResult == null ? null : ragResult.answer(), ""));
    payload.put("citations", ragCitations);
    return ApiResponse.ok(payload);
  }

  private Map<String, Object> buildDashboardData() {
    if (useJdbc()) {
      try {
        return buildDashboardFromDb();
      } catch (Exception ex) {
        jdbcEnabled = false;
        log.warn("读取数据库运营指标失败，降级到 CSV: {}", ex.getMessage());
      }
    }

    try {
      return buildDashboardFromCsv();
    } catch (Exception e) {
      log.warn("读取运营CSV失败，使用静态数据: {}", e.getMessage());
      return buildDashboardStatic();
    }
  }

  private Map<String, Object> buildDashboardFromDb() {
    List<Map<String, Object>> rows = new ArrayList<>(jdbcTemplate.queryForList(SELECT_LAST7_METRIC_SQL));
    if (rows.size() < 7) {
      throw new IllegalStateException("数据库运营指标不足 7 行");
    }
    Collections.reverse(rows);

    List<String> dates = new ArrayList<>();
    List<Double> occTrend = new ArrayList<>();
    List<Integer> revTrend = new ArrayList<>();
    List<Double> cancelTrend = new ArrayList<>();
    List<Double> scoreTrend = new ArrayList<>();
    List<Double> negTrend = new ArrayList<>();
    for (Map<String, Object> row : rows) {
      LocalDate bizDate = toLocalDate(row.get("biz_date"));
      dates.add(String.format("%02d-%02d", bizDate.getMonthValue(), bizDate.getDayOfMonth()));
      occTrend.add(toDouble(row.get("occupancy_rate"), 0.8));
      revTrend.add((int) Math.round(toDouble(row.get("revenue"), 120000)));
      cancelTrend.add(toDouble(row.get("cancellation_rate"), 0.16));
      scoreTrend.add(toDouble(row.get("review_score"), 4.4));
      negTrend.add(toDouble(row.get("negative_rate"), 0.06));
    }
    return buildDashboardResult(dates, occTrend, revTrend, cancelTrend, scoreTrend, negTrend);
  }

  private Map<String, Object> buildDashboardFromCsv() throws Exception {
    List<String[]> rows = new ArrayList<>();
    int idxDate = -1;
    int idxOcc = -1;
    int idxRev = -1;
    int idxCancel = -1;
    int idxScore = -1;
    int idxNeg = -1;
    try (BufferedReader br = new BufferedReader(new FileReader(CSV_PATH))) {
      String headerLine = br.readLine();
      if (headerLine == null) {
        throw new Exception("空文件");
      }
      String[] headers = headerLine.split(",");
      for (int i = 0; i < headers.length; i++) {
        switch (headers[i].trim()) {
          case "date" -> idxDate = i;
          case "occupancy_rate" -> idxOcc = i;
          case "daily_revenue" -> idxRev = i;
          case "cancellation_rate" -> idxCancel = i;
          case "review_score" -> idxScore = i;
          case "negative_rate" -> idxNeg = i;
          default -> {
          }
        }
      }
      String line;
      while ((line = br.readLine()) != null) {
        rows.add(line.split(","));
      }
    }
    if (rows.size() < 7) {
      throw new Exception("数据不足7行");
    }

    List<String[]> last7 = rows.subList(rows.size() - 7, rows.size());
    List<String> dates = new ArrayList<>();
    List<Double> occTrend = new ArrayList<>();
    List<Integer> revTrend = new ArrayList<>();
    List<Double> cancelTrend = new ArrayList<>();
    List<Double> scoreTrend = new ArrayList<>();
    List<Double> negTrend = new ArrayList<>();
    DateTimeFormatter fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    for (String[] row : last7) {
      if (idxDate >= 0 && idxDate < row.length) {
        LocalDate d = LocalDate.parse(row[idxDate].trim(), fmt);
        dates.add(String.format("%02d-%02d", d.getMonthValue(), d.getDayOfMonth()));
      }
      occTrend.add(idxOcc >= 0 ? Double.parseDouble(row[idxOcc].trim()) : 0.80);
      revTrend.add(idxRev >= 0 ? (int) Double.parseDouble(row[idxRev].trim()) : 120000);
      cancelTrend.add(idxCancel >= 0 ? Double.parseDouble(row[idxCancel].trim()) : 0.16);
      scoreTrend.add(idxScore >= 0 ? Double.parseDouble(row[idxScore].trim()) : 4.4);
      negTrend.add(idxNeg >= 0 ? Double.parseDouble(row[idxNeg].trim()) : 0.06);
    }
    return buildDashboardResult(dates, occTrend, revTrend, cancelTrend, scoreTrend, negTrend);
  }

  private Map<String, Object> buildDashboardResult(
      List<String> dates,
      List<Double> occTrend,
      List<Integer> revTrend,
      List<Double> cancelTrend,
      List<Double> scoreTrend,
      List<Double> negTrend
  ) {
    int latestIndex = occTrend.size() - 1;
    double latestOcc = occTrend.get(latestIndex);
    int latestRev = revTrend.get(latestIndex);
    double latestCancel = cancelTrend.get(latestIndex);
    double latestScore = scoreTrend.get(latestIndex);
    double latestNeg = negTrend.get(latestIndex);
    int occupiedRooms = (int) Math.round(latestOcc * TOTAL_ROOMS);

    double adrBase = latestOcc > 0 ? latestRev / (latestOcc * TOTAL_ROOMS) : 668.0;
    List<Double> adrTrend = new ArrayList<>();
    for (int i = 0; i < revTrend.size(); i++) {
      double occ = occTrend.get(i);
      adrTrend.add(occ > 0 ? revTrend.get(i) / (occ * TOTAL_ROOMS) : adrBase);
    }
    List<Integer> occupiedRoomTrend = occTrend.stream()
        .map(o -> (int) Math.round(o * TOTAL_ROOMS))
        .toList();
    List<Double> requestTrend = occTrend.stream().map(o -> Math.round(o * 55) * 1.0).toList();
    List<Double> repeatTrend = occTrend.stream().map(o -> Math.round(o * 13) * 1.0).toList();
    String tip = latestNeg > 0.10 ? "差评率偏高，建议排查保洁与前台响应。"
        : latestCancel > 0.20 ? "取消率偏高，建议检查预订政策与渠道管理。"
        : "运营指标正常，继续保持服务质量。";

    Map<String, Object> result = new HashMap<>();
    result.put("availableRooms", TOTAL_ROOMS);
    result.put("occupiedRooms", occupiedRooms);
    result.put("occupancyRate", latestOcc);
    result.put("dailyRevenue", latestRev);
    result.put("cancellationRate", latestCancel);
    result.put("reviewScore", latestScore);
    result.put("negativeRate", latestNeg);
    result.put("tip", tip);
    result.put("dates", dates);
    result.put("occupancyTrend", occTrend);
    result.put("occupiedRoomTrend", occupiedRoomTrend);
    result.put("revenueTrend", revTrend);
    result.put("cancellationRateTrend", cancelTrend);
    result.put("adrTrend", adrTrend);
    result.put("requestTrend", requestTrend);
    result.put("repeatGuestTrend", repeatTrend);
    result.put("scoreTrend", scoreTrend);
    result.put("negativeRateTrend", negTrend);
    return result;
  }

  private Map<String, Object> buildDashboardStatic() {
    return Map.ofEntries(
        Map.entry("availableRooms", TOTAL_ROOMS),
        Map.entry("occupiedRooms", (int) Math.round(0.82 * TOTAL_ROOMS)),
        Map.entry("occupancyRate", 0.82),
        Map.entry("dailyRevenue", 128000),
        Map.entry("cancellationRate", 0.16),
        Map.entry("reviewScore", 4.5),
        Map.entry("negativeRate", 0.06),
        Map.entry("tip", "当前差评率轻微上升，建议优先排查保洁与前台高峰时段响应。"),
        Map.entry("dates", List.of("03-07", "03-08", "03-09", "03-10", "03-11", "03-12", "03-13")),
        Map.entry("occupancyTrend", List.of(0.74, 0.76, 0.79, 0.81, 0.82, 0.80, 0.83)),
        Map.entry("occupiedRoomTrend", List.of(89, 91, 95, 97, 98, 96, 100)),
        Map.entry("revenueTrend", List.of(102000, 108000, 112000, 119000, 128000, 124000, 131000)),
        Map.entry("cancellationRateTrend", List.of(0.19, 0.18, 0.17, 0.16, 0.15, 0.16, 0.15)),
        Map.entry("adrTrend", List.of(620.0, 635.0, 640.0, 655.0, 668.0, 660.0, 672.0)),
        Map.entry("requestTrend", List.of(36.0, 39.0, 41.0, 43.0, 45.0, 44.0, 46.0)),
        Map.entry("repeatGuestTrend", List.of(9.0, 9.0, 10.0, 10.0, 11.0, 10.0, 11.0)),
        Map.entry("scoreTrend", List.of(4.3, 4.4, 4.3, 4.5, 4.5, 4.4, 4.6)),
        Map.entry("negativeRateTrend", List.of(0.08, 0.07, 0.07, 0.06, 0.06, 0.07, 0.05))
    );
  }

  @SuppressWarnings("unchecked")
  private Map<String, Object> buildForecastFeatures(Map<String, Object> dashboard) {
    List<Double> occupancyTrend = (List<Double>) dashboard.get("occupancyTrend");
    List<Integer> revenueTrend = (List<Integer>) dashboard.get("revenueTrend");
    List<Double> cancellationTrend = (List<Double>) dashboard.get("cancellationRateTrend");
    List<Double> adrTrend = (List<Double>) dashboard.get("adrTrend");
    List<Double> requestTrend = (List<Double>) dashboard.get("requestTrend");
    List<Double> repeatGuestTrend = (List<Double>) dashboard.get("repeatGuestTrend");
    List<Double> scoreTrend = (List<Double>) dashboard.get("scoreTrend");
    List<Double> negativeRateTrend = (List<Double>) dashboard.get("negativeRateTrend");
    LocalDate targetDate = LocalDate.now().plusDays(1);

    double occRoll7 = occupancyTrend.stream().mapToDouble(Double::doubleValue).average().orElse(0.8);
    double revRoll7 = revenueTrend.stream().mapToInt(Integer::intValue).average().orElse(120000);
    double latestOcc = occupancyTrend.get(occupancyTrend.size() - 1);
    double avgRoomPrice = revRoll7 / Math.max(latestOcc * TOTAL_ROOMS, 1.0);
    int weekendNights = targetDate.getDayOfWeek().getValue() >= 6 ? 1 : 0;
    int weekNights = weekendNights == 1 ? 1 : 2;
    int totalNights = weekendNights + weekNights;

    Map<String, Object> features = new HashMap<>();
    features.put("day_of_week", targetDate.getDayOfWeek().getValue() - 1);
    features.put("month", targetDate.getMonthValue());
    features.put("week_of_year", targetDate.get(IsoFields.WEEK_OF_WEEK_BASED_YEAR));
    features.put("is_weekend", targetDate.getDayOfWeek().getValue() >= 6 ? 1 : 0);
    features.put("is_holiday", 0);
    features.put("weather_score", 4);
    features.put("nearby_event", 1);
    features.put("occ_lag1", occupancyTrend.get(occupancyTrend.size() - 1));
    features.put("occ_lag7", occupancyTrend.get(0));
    features.put("occ_roll7", occRoll7);
    features.put("rev_lag1", revenueTrend.get(revenueTrend.size() - 1));
    features.put("rev_lag7", revenueTrend.get(0));
    features.put("rev_roll7", revRoll7);
    features.put("cancel_lag1", cancellationTrend.get(cancellationTrend.size() - 1));
    features.put("cancel_lag7", cancellationTrend.get(0));
    features.put("cancel_roll7", cancellationTrend.stream().mapToDouble(Double::doubleValue).average().orElse(0.16));
    features.put("adr_lag1", adrTrend.get(adrTrend.size() - 1));
    features.put("adr_lag7", adrTrend.get(0));
    features.put("adr_roll7", adrTrend.stream().mapToDouble(Double::doubleValue).average().orElse(avgRoomPrice));
    features.put("booking_lag1", latestOcc * TOTAL_ROOMS);
    features.put("booking_lag7", occupancyTrend.get(0) * TOTAL_ROOMS);
    features.put("booking_roll7", occRoll7 * TOTAL_ROOMS);
    features.put("request_lag1", requestTrend.get(requestTrend.size() - 1));
    features.put("request_lag7", requestTrend.get(0));
    features.put("request_roll7", requestTrend.stream().mapToDouble(Double::doubleValue).average().orElse(42.0));
    features.put("repeat_guest_lag1", repeatGuestTrend.get(repeatGuestTrend.size() - 1));
    features.put("repeat_guest_lag7", repeatGuestTrend.get(0));
    features.put("repeat_guest_roll7", repeatGuestTrend.stream().mapToDouble(Double::doubleValue).average().orElse(10.0));
    features.put("review_lag1", scoreTrend.get(scoreTrend.size() - 1));
    features.put("review_lag7", scoreTrend.get(0));
    features.put("review_roll7", scoreTrend.stream().mapToDouble(Double::doubleValue).average().orElse(4.4));
    features.put("negative_lag1", negativeRateTrend.get(negativeRateTrend.size() - 1));
    features.put("negative_lag7", negativeRateTrend.get(0));
    features.put("negative_roll7", negativeRateTrend.stream().mapToDouble(Double::doubleValue).average().orElse(0.06));
    features.put("lead_time", 18);
    features.put("weekend_nights", weekendNights);
    features.put("week_nights", weekNights);
    features.put("total_nights", totalNights);
    features.put("weekend_ratio", totalNights == 0 ? 0 : (double) weekendNights / (totalNights + 1));
    features.put("adults", 2);
    features.put("children", 0);
    features.put("babies", 0);
    features.put("total_guests", 2);
    features.put("family_flag", 0);
    features.put("avg_price", avgRoomPrice);
    features.put("price_per_guest", avgRoomPrice / 2.0);
    features.put("price_per_night", avgRoomPrice / Math.max(totalNights, 1));
    features.put("special_requests", 1);
    features.put("request_per_guest", 0.5);
    features.put("repeated_guest", 0);
    features.put("previous_cancellations", 0);
    features.put("previous_bookings_not_canceled", 1);
    features.put("history_total", 1);
    features.put("history_cancel_ratio", 0);
    features.put("parking_spaces", 0);
    features.put("hotel_type_code", 0);
    features.put("booking_changes", 0);
    features.put("days_in_waiting_list", 0);
    features.put("meal_plan", "basic");
    features.put("market_segment", "direct");
    features.put("distribution_channel", "direct");
    features.put("deposit_type", "no deposit");
    features.put("customer_type", "transient");
    features.put("room_type", "room_type_1");
    features.put("lead_time_bucket", "w1_2");
    return features;
  }

  private Map<String, Object> buildDecisionMetrics(
      Map<String, Object> dashboard,
      Map<String, Object> occResult,
      Map<String, Object> revenueResult,
      Map<String, Object> cancellationResult,
      Map<String, Object> features
  ) {
    Map<String, Object> metrics = new HashMap<>();
    metrics.put("current_occupancy", toDouble(dashboard.get("occupancyRate"), 0.0));
    metrics.put(
        "predicted_occupancy",
        toDouble(occResult.get("predicted_occupancy"), toDouble(dashboard.get("occupancyRate"), 0.0))
    );
    metrics.put("current_revenue", toDouble(dashboard.get("dailyRevenue"), 0.0));
    metrics.put(
        "predicted_revenue",
        toDouble(revenueResult.get("predicted_revenue"), toDouble(dashboard.get("dailyRevenue"), 0.0))
    );
    metrics.put("current_cancellation_rate", toDouble(dashboard.get("cancellationRate"), 0.0));
    metrics.put(
        "predicted_cancellation_rate",
        toDouble(
            cancellationResult.get("predicted_cancellation_rate"),
            toDouble(dashboard.get("cancellationRate"), 0.0)
        )
    );
    metrics.put("review_score", toDouble(dashboard.get("reviewScore"), 0.0));
    metrics.put("negative_rate", toDouble(dashboard.get("negativeRate"), 0.0));
    metrics.put("is_holiday", toInteger(features.get("is_holiday"), 0));
    metrics.put("nearby_event", toInteger(features.get("nearby_event"), 0));
    return metrics;
  }

  private void bootstrapJdbcMetrics() {
    if (!useJdbc()) {
      return;
    }
    try {
      jdbcTemplate.execute(CREATE_METRIC_TABLE_SQL);
      ensureMetricTableSchema();
      Integer count = jdbcTemplate.queryForObject(COUNT_METRIC_SQL, Integer.class);
      if (count != null && count > 0) {
        return;
      }
      upsertMetric("2026-02-17", 0.74, 102000, 0.19, 4.30, 0.08);
      upsertMetric("2026-02-18", 0.76, 108000, 0.18, 4.33, 0.07);
      upsertMetric("2026-02-19", 0.79, 112000, 0.17, 4.35, 0.07);
      upsertMetric("2026-02-20", 0.81, 119000, 0.16, 4.42, 0.06);
      upsertMetric("2026-02-21", 0.82, 128000, 0.15, 4.50, 0.06);
      upsertMetric("2026-02-22", 0.80, 124000, 0.16, 4.48, 0.07);
      upsertMetric("2026-02-23", 0.83, 131000, 0.15, 4.52, 0.05);
    } catch (DataAccessException ex) {
      jdbcEnabled = false;
      log.warn("初始化数据库运营指标失败: {}", ex.getMessage());
    }
  }

  private void ensureMetricTableSchema() {
    Integer count = jdbcTemplate.queryForObject(HAS_CANCELLATION_RATE_COLUMN_SQL, Integer.class);
    if (count == null || count == 0) {
      jdbcTemplate.execute(ALTER_METRIC_TABLE_SQL);
    }
  }

  private void upsertMetric(
      String bizDate,
      double occupancyRate,
      double revenue,
      double cancellationRate,
      double reviewScore,
      double negativeRate
  ) {
    jdbcTemplate.update(
        INSERT_METRIC_SQL,
        Date.valueOf(LocalDate.parse(bizDate)),
        occupancyRate,
        revenue,
        cancellationRate,
        reviewScore,
        negativeRate
    );
  }

  private boolean useJdbc() {
    return jdbcTemplate != null && jdbcEnabled;
  }

  private LocalDate toLocalDate(Object value) {
    if (value instanceof LocalDate localDate) {
      return localDate;
    }
    if (value instanceof Date date) {
      return date.toLocalDate();
    }
    if (value instanceof Timestamp ts) {
      return ts.toLocalDateTime().toLocalDate();
    }
    return LocalDate.parse(String.valueOf(value));
  }

  private double toDouble(Object value, double fallback) {
    if (value == null) {
      return fallback;
    }
    if (value instanceof Number number) {
      return number.doubleValue();
    }
    try {
      return Double.parseDouble(String.valueOf(value));
    } catch (NumberFormatException ex) {
      return fallback;
    }
  }

  private int toInteger(Object value, int fallback) {
    if (value == null) {
      return fallback;
    }
    if (value instanceof Number number) {
      return number.intValue();
    }
    try {
      return Integer.parseInt(String.valueOf(value));
    } catch (NumberFormatException ex) {
      return fallback;
    }
  }

  private Map<String, Object> safeMap(Map<String, Object> value) {
    return value == null ? Collections.emptyMap() : value;
  }

  private String toNonBlankString(Object value, String fallback) {
    if (value == null) {
      return fallback;
    }
    String text = String.valueOf(value).trim();
    return text.isEmpty() ? fallback : text;
  }

  private List<String> toStringList(Object value, String fallback) {
    if (value instanceof List<?> list && !list.isEmpty()) {
      List<String> result = new ArrayList<>();
      for (Object item : list) {
        if (item != null) {
          String text = String.valueOf(item).trim();
          if (!text.isEmpty()) {
            result.add(text);
          }
        }
      }
      if (!result.isEmpty()) {
        return result;
      }
    }
    return List.of(fallback);
  }
}
