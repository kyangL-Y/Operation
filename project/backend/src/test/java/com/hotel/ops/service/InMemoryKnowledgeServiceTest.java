package com.hotel.ops.service;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

import com.hotel.ops.service.impl.InMemoryKnowledgeService;
import org.junit.jupiter.api.Test;

class InMemoryKnowledgeServiceTest {

  @Test
  void should_search_return_hits() {
    InMemoryKnowledgeService service = new InMemoryKnowledgeService();
    var hits = service.search("客户投诉 异味 如何处理", 3);
    assertFalse(hits.isEmpty());
  }

  @Test
  void should_add_document_success() {
    InMemoryKnowledgeService service = new InMemoryKnowledgeService();
    service.addDoc("测试文档", "前台高峰期排队处理建议");
    var docs = service.listDocs();
    assertTrue(docs.stream().anyMatch(d -> d.title().equals("测试文档")));
  }

  @Test
  void should_return_empty_when_query_not_match() {
    InMemoryKnowledgeService service = new InMemoryKnowledgeService();
    var hits = service.search("不存在的关键词12345", 3);
    assertTrue(hits.isEmpty());
  }

  @Test
  void should_limit_search_results_by_topK() {
    InMemoryKnowledgeService service = new InMemoryKnowledgeService();
    service.addDoc("投诉处理补充方案", "出现连续投诉时，优先由值班经理介入。");
    service.addDoc("投诉升级处理", "连续差评应触发升级处置流程。");
    var hits = service.search("投诉 处理", 2);
    assertEquals(2, hits.size());
  }
}
