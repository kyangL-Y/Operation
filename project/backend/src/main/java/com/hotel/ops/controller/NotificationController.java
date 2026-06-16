package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.model.Notification;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/notifications")
public class NotificationController {

    private final Map<Long, List<Notification>> userNotifications = new ConcurrentHashMap<>();
    private final AtomicLong idGen = new AtomicLong(100);

    public NotificationController() {
        // 初始化演示数据
        List<Notification> demoList = new ArrayList<>();
        demoList.add(new Notification(1, 0, "系统启动成功", "酒店运营支持系统已成功启动，所有服务运行正常。", "SUCCESS", false, LocalDateTime.now()));
        demoList.add(new Notification(2, 0, "预测服务检测", "经营预测服务连接正常，预测功能已就绪。", "INFO", true, LocalDateTime.now().minusHours(1)));
        demoList.add(new Notification(3, 0, "入住率告警", "当前入住率低于预警阈值 70%，请关注渠道策略。", "ALERT", false, LocalDateTime.now().minusHours(2)));
        demoList.add(new Notification(4, 0, "差评率上升", "近7日差评率较上周上升 2.3%，建议排查高频投诉原因。", "WARNING", false, LocalDateTime.now().minusDays(1)));
        userNotifications.put(0L, demoList);
    }

    @GetMapping
    public ApiResponse<List<Notification>> list() {
        List<Notification> all = userNotifications.getOrDefault(0L, new ArrayList<>());
        return ApiResponse.ok(all);
    }

    @PostMapping
    public ApiResponse<Notification> create(@RequestBody Map<String, String> req) {
        String title = req.getOrDefault("title", "").trim();
        String content = req.getOrDefault("content", "").trim();
        String type = req.getOrDefault("type", "INFO").trim().toUpperCase();
        if (title.isEmpty() || content.isEmpty()) {
            return ApiResponse.fail(400, "标题和内容不能为空");
        }
        if (!List.of("INFO", "WARNING", "ALERT", "SUCCESS").contains(type)) {
            type = "INFO";
        }
        Notification notification = new Notification(
                idGen.incrementAndGet(),
                0,
                title,
                content,
                type,
                false,
                LocalDateTime.now()
        );
        List<Notification> list = new ArrayList<>(userNotifications.getOrDefault(0L, new ArrayList<>()));
        list.add(0, notification);
        userNotifications.put(0L, list);
        return ApiResponse.ok(notification);
    }

    @GetMapping("/unread-count")
    public ApiResponse<Map<String, Long>> unreadCount() {
        List<Notification> all = userNotifications.getOrDefault(0L, new ArrayList<>());
        long count = all.stream().filter(n -> !n.isRead()).count();
        return ApiResponse.ok(Map.of("count", count));
    }

    @PutMapping("/{id}/read")
    public ApiResponse<Void> markRead(@PathVariable long id) {
        List<Notification> list = userNotifications.getOrDefault(0L, new ArrayList<>());
        for (int i = 0; i < list.size(); i++) {
            Notification n = list.get(i);
            if (n.id() == id) {
                list.set(i, new Notification(n.id(), n.userId(), n.title(), n.content(), n.type(), true, n.createdAt()));
                break;
            }
        }
        return ApiResponse.ok(null);
    }

    @PutMapping("/read-all")
    public ApiResponse<Void> markAllRead() {
        List<Notification> list = userNotifications.getOrDefault(0L, new ArrayList<>());
        List<Notification> updated = new ArrayList<>();
        for (Notification n : list) {
            updated.add(new Notification(n.id(), n.userId(), n.title(), n.content(), n.type(), true, n.createdAt()));
        }
        userNotifications.put(0L, updated);
        return ApiResponse.ok(null);
    }
}
