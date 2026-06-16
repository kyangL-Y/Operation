package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.model.SystemConfig;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/settings")
public class ConfigController {

    private final Map<String, SystemConfig> configs = new ConcurrentHashMap<>();

    public ConfigController() {
        LocalDateTime now = LocalDateTime.now();
        configs.put("ml.service.url", new SystemConfig("ml.service.url", "http://localhost:5000", "预测服务位置", now));
        configs.put("ml.enabled", new SystemConfig("ml.enabled", "true", "是否启用预测服务", now));
        configs.put("alert.occupancy.threshold", new SystemConfig("alert.occupancy.threshold", "0.7", "入住率告警阈值", now));
        configs.put("alert.cancellation.threshold", new SystemConfig("alert.cancellation.threshold", "0.15", "取消率告警阈值", now));
        configs.put("alert.negative.threshold", new SystemConfig("alert.negative.threshold", "0.12", "差评率告警阈值", now));
        configs.put("system.name", new SystemConfig("system.name", "酒店运营支持系统", "系统名称", now));
        configs.put("system.language", new SystemConfig("system.language", "zh-CN", "默认语言", now));
    }

    @GetMapping
    public ApiResponse<Map<String, String>> getAll() {
        Map<String, String> result = new ConcurrentHashMap<>();
        configs.forEach((k, v) -> result.put(k, v.configValue()));
        return ApiResponse.ok(result);
    }

    @GetMapping("/{key}")
    public ApiResponse<SystemConfig> get(@PathVariable String key) {
        SystemConfig config = configs.get(key);
        if (config == null) {
            return ApiResponse.ok(new SystemConfig(key, "", "", LocalDateTime.now()));
        }
        return ApiResponse.ok(config);
    }

    @PutMapping("/{key}")
    public ApiResponse<SystemConfig> update(@PathVariable String key, @RequestBody Map<String, String> body) {
        String value = body.get("value");
        SystemConfig existing = configs.get(key);
        String desc = existing != null ? existing.description() : "";
        SystemConfig updated = new SystemConfig(key, value, desc, LocalDateTime.now());
        configs.put(key, updated);
        return ApiResponse.ok(updated);
    }
}
