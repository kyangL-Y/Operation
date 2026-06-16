package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.model.AuditLog;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/audit-logs")
public class AuditController {

    private final List<AuditLog> logs = new CopyOnWriteArrayList<>();
    private final AtomicLong idGen = new AtomicLong(100);

    public AuditController() {
        // 初始化演示数据
        logs.add(new AuditLog(1, 1, "admin", "LOGIN", "AUTH", "管理员登录系统", "127.0.0.1", LocalDateTime.now()));
        logs.add(new AuditLog(2, 1, "admin", "CREATE_USER", "ADMIN", "创建用户: test001", "127.0.0.1", LocalDateTime.now().minusMinutes(30)));
        logs.add(new AuditLog(3, 3, "staff", "LOGIN", "AUTH", "员工登录系统", "192.168.1.100", LocalDateTime.now().minusHours(1)));
        logs.add(new AuditLog(4, 1, "admin", "UPDATE_ROLE", "ADMIN", "更新用户角色: manager -> ADMIN", "127.0.0.1", LocalDateTime.now().minusHours(2)));
        logs.add(new AuditLog(5, 3, "staff", "CREATE_DOC", "KB", "创建资料文档: 前台接待流程", "192.168.1.100", LocalDateTime.now().minusDays(1)));
        logs.add(new AuditLog(6, 1, "admin", "DELETE_DOC", "KB", "删除知识文档: 旧版流程", "127.0.0.1", LocalDateTime.now().minusDays(2)));
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        List<AuditLog> sorted = new ArrayList<>(logs);
        sorted.sort(Comparator.comparing(AuditLog::createdAt).reversed());

        int total = sorted.size();
        int from = page * size;
        int to = Math.min(from + size, total);
        List<AuditLog> content = from < total ? sorted.subList(from, to) : List.of();

        return ApiResponse.ok(Map.of(
            "content", content,
            "totalElements", total,
            "totalPages", (total + size - 1) / size,
            "page", page,
            "size", size
        ));
    }

    public void log(long userId, String username, String action, String module, String detail, String ipAddress) {
        logs.add(new AuditLog(
            idGen.incrementAndGet(),
            userId,
            username,
            action,
            module,
            detail,
            ipAddress,
            LocalDateTime.now()
        ));
    }
}
