USE hotel_ops;

INSERT INTO sys_user (username, display_name, password_hash, role_code, status) VALUES
('admin', '系统管理员', 'admin123', 'ADMIN', 1),
('manager', '值班经理', 'manager123', 'MANAGER', 1),
('staff', '普通员工', 'staff123', 'STAFF', 1)
ON DUPLICATE KEY UPDATE username = VALUES(username);

INSERT INTO kb_document (title, content, source_type) VALUES
('投诉处理流程', '先致歉并记录信息，10分钟内响应，必要时提供换房或补偿，并完成回访。', 'seed'),
('夜间应急处理', '夜间噪音投诉先电话提醒，再上门协调，必要时升级值班经理。', 'seed'),
('客房异味处理', '确认异味来源后执行通风和深度清洁，无法快速处理时优先为客户换房。', 'seed');

INSERT INTO ops_daily_metric (biz_date, occupancy_rate, revenue, cancellation_rate, review_score, negative_rate) VALUES
('2026-02-17', 0.74, 102000, 0.19, 4.30, 0.08),
('2026-02-18', 0.76, 108000, 0.18, 4.33, 0.07),
('2026-02-19', 0.79, 112000, 0.17, 4.35, 0.07),
('2026-02-20', 0.81, 119000, 0.16, 4.42, 0.06),
('2026-02-21', 0.82, 128000, 0.15, 4.50, 0.06),
('2026-02-22', 0.80, 124000, 0.16, 4.48, 0.07),
('2026-02-23', 0.83, 131000, 0.15, 4.52, 0.05)
ON DUPLICATE KEY UPDATE revenue = VALUES(revenue);
