package com.hotel.ops.service;

import com.hotel.ops.dto.RagAskResult;

public interface RagService {
  RagAskResult ask(String question);
  RagAskResult deepSearch(String question);
}

