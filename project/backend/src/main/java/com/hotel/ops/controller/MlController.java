package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.service.MlServiceClient;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * ML 模型接口 - 运营预测与决策分析。
 * 代理调用 Python ML API 服务 (port 5000)。
 */
@RestController
@RequestMapping("/api/ml")
public class MlController {

    private final MlServiceClient mlClient;

    public MlController(MlServiceClient mlClient) {
        this.mlClient = mlClient;
    }

    /** 入住率预测。 */
    @PostMapping("/predict-occupancy")
    @SuppressWarnings("unchecked")
    public ApiResponse<Map<String, Object>> predictOccupancy(@RequestBody Map<String, Object> req) {
        Map<String, Object> features = (Map<String, Object>) req.get("features");
        if (features == null || features.isEmpty()) {
            return ApiResponse.fail(400, "features 不能为空");
        }
        if (!mlClient.isAvailable()) {
            return ApiResponse.fail(503, "预测服务暂未连接，请检查预测服务状态。");
        }
        Map<String, Object> result = mlClient.occupancyPredict(features);
        return ApiResponse.ok(result);
    }

    /** 营收预测。 */
    @PostMapping("/predict-revenue")
    @SuppressWarnings("unchecked")
    public ApiResponse<Map<String, Object>> predictRevenue(@RequestBody Map<String, Object> req) {
        Map<String, Object> features = (Map<String, Object>) req.get("features");
        if (features == null || features.isEmpty()) {
            return ApiResponse.fail(400, "features 不能为空");
        }
        if (!mlClient.isAvailable()) {
            return ApiResponse.fail(503, "预测服务暂未连接，请检查预测服务状态。");
        }
        Map<String, Object> result = mlClient.revenuePredict(features);
        return ApiResponse.ok(result);
    }

    /** 订单取消风险预测。 */
    @PostMapping("/predict-cancellation")
    @SuppressWarnings("unchecked")
    public ApiResponse<Map<String, Object>> predictCancellation(@RequestBody Map<String, Object> req) {
        Map<String, Object> features = (Map<String, Object>) req.get("features");
        if (features == null || features.isEmpty()) {
            return ApiResponse.fail(400, "features 不能为空");
        }
        if (!mlClient.isAvailable()) {
            return ApiResponse.fail(503, "预测服务暂未连接，请检查预测服务状态。");
        }
        Map<String, Object> result = mlClient.cancellationPredict(features);
        return ApiResponse.ok(result);
    }

    /** 运营决策分析。 */
    @PostMapping("/decision/analyze")
    @SuppressWarnings("unchecked")
    public ApiResponse<Map<String, Object>> analyzeDecision(@RequestBody Map<String, Object> req) {
        Map<String, Object> metrics = (Map<String, Object>) req.get("metrics");
        if (metrics == null || metrics.isEmpty()) {
            return ApiResponse.fail(400, "metrics 不能为空");
        }
        if (!mlClient.isAvailable()) {
            return ApiResponse.fail(503, "预测服务暂未连接，请检查预测服务状态。");
        }
        Map<String, Object> result = mlClient.decisionAnalyze(metrics);
        return ApiResponse.ok(result);
    }

    /** 预测服务状态检查。 */
    @GetMapping("/status")
    public ApiResponse<Map<String, Object>> status() {
        boolean available = mlClient.isAvailable();
        if (!available) {
            return ApiResponse.ok(Map.of(
                    "ml_service", "offline",
                    "url", "http://localhost:5000",
                    "retrievalMode", "offline",
                    "generationMode", "offline"
            ));
        }
        Map<String, Object> health = mlClient.healthStatus();
        return ApiResponse.ok(Map.of(
                "ml_service", "running",
                "url", "http://localhost:5000",
                "retrievalMode", String.valueOf(health.getOrDefault("retrievalMode", "unknown")),
                "generationMode", String.valueOf(health.getOrDefault("generationMode", "unknown")),
                "knowledgeCount", health.getOrDefault("knowledgeCount", health.getOrDefault("knowledge_count", 0)),
                "deepseekConfigured", health.getOrDefault("deepseekConfigured", false)
        ));
    }
}
