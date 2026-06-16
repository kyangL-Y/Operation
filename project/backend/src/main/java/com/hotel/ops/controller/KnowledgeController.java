package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.dto.KnowledgeDocRequest;
import com.hotel.ops.model.KnowledgeDoc;
import com.hotel.ops.service.KnowledgeService;
import jakarta.validation.Valid;
import java.util.List;
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
@RequestMapping("/api/kb")
public class KnowledgeController {

  private final KnowledgeService knowledgeService;

  public KnowledgeController(KnowledgeService knowledgeService) {
    this.knowledgeService = knowledgeService;
  }

  @PostMapping("/docs")
  public ApiResponse<KnowledgeDoc> addDoc(@Valid @RequestBody KnowledgeDocRequest request) {
    return ApiResponse.ok(knowledgeService.addDoc(request.title(), request.content()));
  }

  @PutMapping("/docs/{id}")
  public ApiResponse<KnowledgeDoc> updateDoc(@PathVariable("id") long id,
                                             @Valid @RequestBody KnowledgeDocRequest request) {
    KnowledgeDoc doc = knowledgeService.updateDoc(id, request.title(), request.content());
    if (doc == null) {
      return ApiResponse.fail(404, "文档不存在");
    }
    return ApiResponse.ok(doc);
  }

  @DeleteMapping("/docs/{id}")
  public ApiResponse<Boolean> deleteDoc(@PathVariable("id") long id) {
    if (!knowledgeService.deleteDoc(id)) {
      return ApiResponse.fail(404, "文档不存在");
    }
    return ApiResponse.ok(true);
  }

  @GetMapping("/docs")
  public ApiResponse<List<KnowledgeDoc>> listDocs() {
    return ApiResponse.ok(knowledgeService.listDocs());
  }

  @GetMapping("/search")
  public ApiResponse<List<KnowledgeDoc>> search(@RequestParam("q") String query,
                                                @RequestParam(value = "topK", defaultValue = "12") int topK) {
    int limit = Math.min(Math.max(topK, 1), 50);
    return ApiResponse.ok(knowledgeService.search(query, limit));
  }
}
