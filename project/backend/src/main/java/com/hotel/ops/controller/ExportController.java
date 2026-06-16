package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.service.MlServiceClient;
import com.hotel.ops.service.RagService;
import java.io.ByteArrayOutputStream;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellRangeAddress;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/ops/export")
public class ExportController {

  private final JdbcTemplate jdbcTemplate;

  public ExportController(
      ObjectProvider<JdbcTemplate> jdbcTemplateProvider,
      @Value("${hotel.jdbc.enabled:false}") boolean jdbcFeatureEnabled
  ) {
    this.jdbcTemplate = jdbcFeatureEnabled ? jdbcTemplateProvider.getIfAvailable() : null;
  }

  @GetMapping("/excel")
  public ResponseEntity<byte[]> exportExcel() throws Exception {
    List<Map<String, Object>> rows = loadMetrics();
    String filename = "hotel_ops_report_" + LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd")) + ".xlsx";

    try (XSSFWorkbook workbook = new XSSFWorkbook()) {
      // ===== Sheet1：当日指标摘要 =====
      Sheet sheet1 = workbook.createSheet("当日指标");
      CellStyle titleStyle = createTitleStyle(workbook);
      CellStyle headerStyle = createHeaderStyle(workbook);
      CellStyle dataStyle = createDataStyle(workbook);

      Row titleRow = sheet1.createRow(0);
      Cell titleCell = titleRow.createCell(0);
      titleCell.setCellValue("酒店运营支持系统 · 经营指标报表");
      titleCell.setCellStyle(titleStyle);
      sheet1.addMergedRegion(new CellRangeAddress(0, 0, 0, 5));

      Row subtitleRow = sheet1.createRow(1);
      subtitleRow.createCell(0).setCellValue("生成时间：" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
      sheet1.addMergedRegion(new CellRangeAddress(1, 1, 0, 5));

      Row headerRow = sheet1.createRow(3);
      String[] headers = {"日期", "入住率", "日营收(元)", "取消率", "评分", "差评率"};
      for (int i = 0; i < headers.length; i++) {
        Cell cell = headerRow.createCell(i);
        cell.setCellValue(headers[i]);
        cell.setCellStyle(headerStyle);
        sheet1.setColumnWidth(i, 5000);
      }

      int rowNum = 4;
      for (Map<String, Object> row : rows) {
        Row dataRow = sheet1.createRow(rowNum++);
        createCell(dataRow, 0, String.valueOf(row.getOrDefault("biz_date", "")), dataStyle);
        createCell(dataRow, 1, formatPct(row.get("occupancy_rate")), dataStyle);
        createCell(dataRow, 2, formatMoney(row.get("revenue")), dataStyle);
        createCell(dataRow, 3, formatPct(row.get("cancellation_rate")), dataStyle);
        createCell(dataRow, 4, String.valueOf(row.getOrDefault("review_score", "-")), dataStyle);
        createCell(dataRow, 5, formatPct(row.get("negative_rate")), dataStyle);
      }

      // ===== Sheet2：数据统计摘要 =====
      Sheet sheet2 = workbook.createSheet("统计摘要");
      if (!rows.isEmpty()) {
        double avgOcc = rows.stream().mapToDouble(r -> toDouble(r.get("occupancy_rate"))).average().orElse(0);
        double avgRev = rows.stream().mapToDouble(r -> toDouble(r.get("revenue"))).average().orElse(0);
        double avgCancel = rows.stream().mapToDouble(r -> toDouble(r.get("cancellation_rate"))).average().orElse(0);
        double avgScore = rows.stream().mapToDouble(r -> toDouble(r.get("review_score"))).average().orElse(0);

        Row sh2Header = sheet2.createRow(0);
        String[] sh2Headers = {"统计项", "数值"};
        for (int i = 0; i < sh2Headers.length; i++) {
          Cell c = sh2Header.createCell(i);
          c.setCellValue(sh2Headers[i]);
          c.setCellStyle(headerStyle);
          sheet2.setColumnWidth(i, 6000);
        }
        String[][] stats = {
            {"统计周期天数", String.valueOf(rows.size())},
            {"平均入住率", String.format("%.1f%%", avgOcc * 100)},
            {"平均日营收", String.format("¥%.0f", avgRev)},
            {"平均取消率", String.format("%.1f%%", avgCancel * 100)},
            {"平均评分", String.format("%.2f", avgScore)}
        };
        for (int i = 0; i < stats.length; i++) {
          Row r = sheet2.createRow(i + 1);
          createCell(r, 0, stats[i][0], dataStyle);
          createCell(r, 1, stats[i][1], dataStyle);
        }
      }

      ByteArrayOutputStream out = new ByteArrayOutputStream();
      workbook.write(out);
      return ResponseEntity.ok()
          .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
          .contentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
          .body(out.toByteArray());
    }
  }

  @GetMapping("/csv")
  public ResponseEntity<byte[]> exportCsv() {
    List<Map<String, Object>> rows = loadMetrics();
    String filename = "hotel_ops_report_" + LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd")) + ".csv";

    StringBuilder sb = new StringBuilder();
    sb.append("日期,入住率,日营收(元),取消率,评分,差评率\n");
    for (Map<String, Object> row : rows) {
      sb.append(row.getOrDefault("biz_date", "")).append(",");
      sb.append(formatPct(row.get("occupancy_rate"))).append(",");
      sb.append(formatMoney(row.get("revenue"))).append(",");
      sb.append(formatPct(row.get("cancellation_rate"))).append(",");
      sb.append(row.getOrDefault("review_score", "-")).append(",");
      sb.append(formatPct(row.get("negative_rate"))).append("\n");
    }

    byte[] bytes = sb.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
    return ResponseEntity.ok()
        .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
        .contentType(MediaType.parseMediaType("text/csv; charset=UTF-8"))
        .body(bytes);
  }

  private List<Map<String, Object>> loadMetrics() {
    if (jdbcTemplate != null) {
      try {
        return jdbcTemplate.queryForList(
            "SELECT biz_date, occupancy_rate, revenue, cancellation_rate, review_score, negative_rate " +
            "FROM ops_daily_metric ORDER BY biz_date DESC LIMIT 30");
      } catch (DataAccessException ignored) {}
    }
    return List.of(
        Map.of("biz_date", "2026-03-25", "occupancy_rate", 0.82, "revenue", 58000, "cancellation_rate", 0.06, "review_score", 4.6, "negative_rate", 0.04),
        Map.of("biz_date", "2026-03-24", "occupancy_rate", 0.78, "revenue", 52000, "cancellation_rate", 0.08, "review_score", 4.5, "negative_rate", 0.05),
        Map.of("biz_date", "2026-03-23", "occupancy_rate", 0.85, "revenue", 62000, "cancellation_rate", 0.05, "review_score", 4.7, "negative_rate", 0.03)
    );
  }

  private CellStyle createTitleStyle(Workbook wb) {
    CellStyle s = wb.createCellStyle();
    Font f = wb.createFont();
    f.setBold(true);
    f.setFontHeightInPoints((short) 14);
    s.setFont(f);
    return s;
  }

  private CellStyle createHeaderStyle(Workbook wb) {
    CellStyle s = wb.createCellStyle();
    Font f = wb.createFont();
    f.setBold(true);
    s.setFont(f);
    s.setFillForegroundColor(IndexedColors.GREY_25_PERCENT.getIndex());
    s.setFillPattern(FillPatternType.SOLID_FOREGROUND);
    s.setBorderBottom(BorderStyle.THIN);
    return s;
  }

  private CellStyle createDataStyle(Workbook wb) {
    CellStyle s = wb.createCellStyle();
    s.setBorderBottom(BorderStyle.THIN);
    s.setBorderLeft(BorderStyle.THIN);
    s.setBorderRight(BorderStyle.THIN);
    return s;
  }

  private void createCell(Row row, int col, String value, CellStyle style) {
    Cell cell = row.createCell(col);
    cell.setCellValue(value);
    cell.setCellStyle(style);
  }

  private String formatPct(Object v) {
    if (v == null) return "-";
    return String.format("%.1f%%", toDouble(v) * 100);
  }

  private String formatMoney(Object v) {
    if (v == null) return "-";
    return String.format("%.0f", toDouble(v));
  }

  private double toDouble(Object v) {
    if (v == null) return 0;
    if (v instanceof Number n) return n.doubleValue();
    try { return Double.parseDouble(String.valueOf(v)); } catch (Exception e) { return 0; }
  }
}
