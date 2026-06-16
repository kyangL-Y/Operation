package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.dto.RagAskRequest;
import com.hotel.ops.dto.RagAskResult;
import com.hotel.ops.service.RagService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/rag")
public class RagController {

  private final RagService ragService;

  public RagController(RagService ragService) {
    this.ragService = ragService;
  }

  @PostMapping("/ask")
  public ApiResponse<RagAskResult> ask(@Valid @RequestBody RagAskRequest request) {
    return ApiResponse.ok(ragService.ask(request.question()));
  }

  @PostMapping("/deep-search")
  public ApiResponse<RagAskResult> deepSearch(@Valid @RequestBody RagAskRequest request) {
    return ApiResponse.ok(ragService.deepSearch(request.question()));
  }
}

