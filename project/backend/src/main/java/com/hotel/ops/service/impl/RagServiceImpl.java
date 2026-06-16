package com.hotel.ops.service.impl;

import com.hotel.ops.dto.RagAskResult;
import com.hotel.ops.model.KnowledgeDoc;
import com.hotel.ops.service.KnowledgeService;
import com.hotel.ops.service.MlServiceClient;
import com.hotel.ops.service.RagService;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

/**
 * RAG 问答服务
 * 优先调用 Python ML 服务（语义检索 + DeepSeek 生成），
 * ML 服务不可用时降级为本地关键词检索 + 模板拼接。
 */
@Service
public class RagServiceImpl implements RagService {

    private static final Logger log = LoggerFactory.getLogger(RagServiceImpl.class);

    private final KnowledgeService knowledgeService;
    private final MlServiceClient mlClient;

    public RagServiceImpl(KnowledgeService knowledgeService, MlServiceClient mlClient) {
        this.knowledgeService = knowledgeService;
        this.mlClient = mlClient;
    }

    @Override
    @SuppressWarnings("unchecked")
    public RagAskResult ask(String question) {
        if (mlClient.isAvailable()) {
            try {
                syncKnowledgeToMl();
                Map<String, Object> result = mlClient.ragAnswer(question);
                return fromRemoteResult(result, "standard");
            } catch (Exception e) {
                log.warn("ML service call failed, falling back to local ask: {}", e.getMessage());
            }
        }
        return localFallback(question);
    }

    @Override
    @SuppressWarnings("unchecked")
    public RagAskResult deepSearch(String question) {
        if (mlClient.isAvailable()) {
            try {
                syncKnowledgeToMl();
                Map<String, Object> result = mlClient.ragDeepSearch(question);
                return fromRemoteResult(result, "deep-search");
            } catch (Exception e) {
                log.warn("ML deep-search call failed, falling back to local deep-search: {}", e.getMessage());
            }
        }
        return localDeepSearch(question);
    }

    private RagAskResult fromRemoteResult(Map<String, Object> result, String defaultMode) {
        String answer = String.valueOf(result.getOrDefault("answer", "-"));
        List<String> citations = normalizeCitations(result.get("citations"));
        List<String> suggestions = normalizeStringList(result.get("suggestions"));
        List<String> queryPlan = normalizeStringList(result.get("queryPlan"));
        String searchDepth = String.valueOf(result.getOrDefault("searchDepth", "standard"));
        String confidence = String.valueOf(result.getOrDefault("confidence", "标准"));
        String mode = String.valueOf(result.getOrDefault("mode", defaultMode));
        String retrievalMode = String.valueOf(result.getOrDefault("retrievalMode", "unknown"));
        String generationMode = String.valueOf(result.getOrDefault("generationMode", "unknown"));
        String source = String.valueOf(result.getOrDefault("source", defaultMode));
        return new RagAskResult(answer, citations, suggestions, queryPlan, searchDepth, confidence, mode,
                retrievalMode, generationMode, source);
    }

    /** 将 Java 端知识库同步到 Python 向量检索服务 */
    private void syncKnowledgeToMl() {
        List<KnowledgeDoc> docs = knowledgeService.listDocs();
        List<Map<String, Object>> docMaps = new ArrayList<>();
        for (KnowledgeDoc doc : docs) {
            docMaps.add(Map.of(
                    "id", String.valueOf(doc.id()),
                    "title", doc.title(),
                    "content", doc.content()
            ));
        }
        if (!docMaps.isEmpty()) {
            mlClient.indexKnowledge(docMaps);
        }
    }

    /** 降级方案：关键词检索 + 模板拼接 */
    private RagAskResult localFallback(String question) {
        List<KnowledgeDoc> hits = knowledgeService.search(question, 3);
        if (hits.isEmpty()) {
            return new RagAskResult(
                    "未检索到足够知识片段。建议补充知识库文档后重试。",
                    List.of(),
                    defaultSuggestions(),
                    List.of(question),
                    "low",
                    "低",
                    "standard",
                    "keyword_fallback",
                    "template_fallback",
                    "java-local-fallback"
            );
        }

        List<String> citations = new ArrayList<>();
        for (KnowledgeDoc hit : hits) {
            citations.add("[" + hit.id() + "] " + hit.title());
        }

        StringBuilder sb = new StringBuilder();
        sb.append("根据当前知识库检索结果，建议如下：");
        for (KnowledgeDoc hit : hits) {
            sb.append("\n- ").append(hit.content());
        }
        sb.append("\n执行时请结合现场情况，由值班经理二次确认。");
        sb.append("\n\n（提示：连接预测与问答服务后可获得更完整的资料匹配和生成回答）");
        return new RagAskResult(
                sb.toString(),
                citations,
                defaultSuggestions(),
                List.of(question),
                hits.size() >= 2 ? "medium" : "low",
                hits.size() >= 2 ? "中" : "低",
                "standard",
                "keyword_fallback",
                "template_fallback",
                "java-local-fallback"
        );
    }

    private RagAskResult localDeepSearch(String question) {
        List<String> queryPlan = buildQueryPlan(question);
        List<KnowledgeDoc> hits = knowledgeService.search(String.join(" ", queryPlan), 5);
        if (hits.isEmpty()) {
            return new RagAskResult(
                    "未检索到足够相关的分析依据，建议补充处理流程、岗位协同或异常处置资料后重试。",
                    List.of(),
                    defaultSuggestions(),
                    queryPlan,
                    "low",
                    "低",
                    "deep-search",
                    "keyword_fallback",
                    "template_fallback",
                    "java-local-deep-search"
            );
        }

        List<String> citations = new ArrayList<>();
        for (KnowledgeDoc hit : hits) {
            citations.add("[" + hit.id() + "] " + hit.title());
        }

        StringBuilder sb = new StringBuilder();
        sb.append("已按深度搜索模式聚合知识证据，建议优先关注以下内容：");
        for (KnowledgeDoc hit : hits) {
            sb.append("\n- ").append(hit.title()).append("：").append(hit.content());
        }
        sb.append("\n\n建议先核对证据，再由值班经理拆分岗位执行动作。");

        String searchDepth = hits.size() >= 3 ? "high" : "medium";
        String confidence = hits.size() >= 3 ? "中高" : "中";
        return new RagAskResult(
                sb.toString(),
                citations,
                defaultSuggestions(),
                queryPlan,
                searchDepth,
                confidence,
                "deep-search",
                "keyword_fallback",
                "template_fallback",
                "java-local-deep-search"
        );
    }

    private List<String> buildQueryPlan(String question) {
        LinkedHashMap<String, String> variants = new LinkedHashMap<>();
        String normalized = question == null ? "" : question.trim();
        if (StringUtils.hasText(normalized)) {
            variants.put(normalized, normalized);
            variants.put("处理流程 " + normalized, "处理流程 " + normalized);
            variants.put(normalized + " 处理流程", normalized + " 处理流程");
            variants.put(normalized + " 值班经理检查项", normalized + " 值班经理检查项");
        }
        return new ArrayList<>(variants.values());
    }

    @SuppressWarnings("unchecked")
    private List<String> normalizeCitations(Object raw) {
        if (!(raw instanceof List<?> rawList)) {
            return List.of();
        }
        List<String> citations = new ArrayList<>();
        for (Object item : rawList) {
            if (item instanceof Map<?, ?> map) {
                Object id = map.get("id");
                Object title = map.get("title");
                Object score = map.get("score");
                StringBuilder sb = new StringBuilder();
                if (id != null) {
                    sb.append("[").append(id).append("] ");
                }
                sb.append(title == null ? "未命名文档" : title);
                if (score != null) {
                    sb.append(" (相关度: ").append(score).append(")");
                }
                citations.add(sb.toString());
            } else if (item != null) {
                citations.add(String.valueOf(item));
            }
        }
        return citations;
    }

    @SuppressWarnings("unchecked")
    private List<String> normalizeStringList(Object raw) {
        if (!(raw instanceof List<?> rawList)) {
            return List.of();
        }
        List<String> values = new ArrayList<>();
        for (Object item : rawList) {
            if (item != null && StringUtils.hasText(String.valueOf(item))) {
                values.add(String.valueOf(item));
            }
        }
        return values;
    }

    private List<String> defaultSuggestions() {
        return List.of(
                "请把结论拆成岗位执行清单",
                "请补充值班经理复盘要点",
                "如果今天入住率承压，这个方案如何与渠道和价格联动？"
        );
    }
}
