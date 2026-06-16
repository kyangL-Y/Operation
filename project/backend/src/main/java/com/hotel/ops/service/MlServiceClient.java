package com.hotel.ops.service;

import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

/**
 * ML API 客户端 - 调用 Python 端的模型服务。
 * 提供：入住率预测 / 营收预测 / 决策分析 / 知识库索引 / RAG 问答
 */
@Service
public class MlServiceClient {

    private final RestTemplate rest = new RestTemplate();
    private final String baseUrl;

    public MlServiceClient(@Value("${ml.api.url:http://localhost:5000}") String baseUrl) {
        this.baseUrl = baseUrl;
    }

    /** 检查 ML 服务是否可用。 */
    public boolean isAvailable() {
        try {
            ResponseEntity<Map> resp = rest.getForEntity(baseUrl + "/api/health", Map.class);
            return resp.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            return false;
        }
    }

    /** 获取 ML 服务健康详情。 */
    @SuppressWarnings("unchecked")
    public Map<String, Object> healthStatus() {
        ResponseEntity<Map> resp = rest.getForEntity(baseUrl + "/api/health", Map.class);
        Map<String, Object> body = resp.getBody();
        if (body == null) {
            return Map.of();
        }
        Object data = body.get("data");
        if (data instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    /** 入住率预测。 */
    @SuppressWarnings("unchecked")
    public Map<String, Object> occupancyPredict(Map<String, Object> features) {
        Map<String, Object> body = Map.of("features", features);
        Map<String, Object> resp = postJson("/api/occupancy/predict", body);
        return (Map<String, Object>) resp.get("data");
    }

    /** 营收预测。 */
    @SuppressWarnings("unchecked")
    public Map<String, Object> revenuePredict(Map<String, Object> features) {
        Map<String, Object> body = Map.of("features", features);
        Map<String, Object> resp = postJson("/api/revenue/predict", body);
        return (Map<String, Object>) resp.get("data");
    }

    /** 订单取消风险预测。 */
    @SuppressWarnings("unchecked")
    public Map<String, Object> cancellationPredict(Map<String, Object> features) {
        Map<String, Object> body = Map.of("features", features);
        Map<String, Object> resp = postJson("/api/cancellation/predict", body);
        return (Map<String, Object>) resp.get("data");
    }

    /** 决策分析。 */
    @SuppressWarnings("unchecked")
    public Map<String, Object> decisionAnalyze(Map<String, Object> metrics) {
        Map<String, Object> body = Map.of("metrics", metrics);
        Map<String, Object> resp = postJson("/api/decision/analyze", body);
        return (Map<String, Object>) resp.get("data");
    }

    /** 知识库索引（将 Java 端文档同步到 Python 向量库）。 */
    public void indexKnowledge(List<Map<String, Object>> documents) {
        Map<String, Object> body = Map.of("documents", documents);
        postJson("/api/knowledge/index", body);
    }

    /** RAG 问答。 */
    @SuppressWarnings("unchecked")
    public Map<String, Object> ragAnswer(String question) {
        Map<String, String> body = Map.of("question", question);
        Map<String, Object> resp = postJson("/api/rag/answer", body);
        return (Map<String, Object>) resp.get("data");
    }

    /** RAG 深度搜索。 */
    @SuppressWarnings("unchecked")
    public Map<String, Object> ragDeepSearch(String question) {
        Map<String, String> body = Map.of("question", question);
        Map<String, Object> resp = postJson("/api/rag/deep-search", body);
        return (Map<String, Object>) resp.get("data");
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> postJson(String path, Object body) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> entity = new HttpEntity<>(body, headers);
        ResponseEntity<Map> resp = rest.postForEntity(baseUrl + path, entity, Map.class);
        return resp.getBody();
    }
}
