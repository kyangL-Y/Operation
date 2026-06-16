package com.hotel.ops.service.impl;

import com.hotel.ops.model.KnowledgeDoc;
import com.hotel.ops.service.KnowledgeService;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;

@Service
public class InMemoryKnowledgeService implements KnowledgeService {

  private static final Logger log = LoggerFactory.getLogger(InMemoryKnowledgeService.class);

  private static final String CREATE_DOC_TABLE_SQL = """
      CREATE TABLE IF NOT EXISTS kb_document (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        title VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        source_type VARCHAR(32) DEFAULT 'manual',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      )
      """;

  private static final String SELECT_ALL_DOCS_SQL = """
      SELECT id, title, content, created_at
      FROM kb_document
      ORDER BY created_at DESC, id DESC
      """;

  private static final String SELECT_DOC_BY_ID_SQL = """
      SELECT id, title, content, created_at
      FROM kb_document
      WHERE id = ?
      """;

  private static final String INSERT_DOC_SQL = """
      INSERT INTO kb_document (title, content, source_type, created_at)
      VALUES (?, ?, ?, ?)
      """;

  private static final String UPDATE_DOC_SQL = """
      UPDATE kb_document
      SET title = ?, content = ?
      WHERE id = ?
      """;

  private static final String DELETE_DOC_SQL = """
      DELETE FROM kb_document
      WHERE id = ?
      """;

  private static final String COUNT_DOC_SQL = "SELECT COUNT(1) FROM kb_document";
  private static final String COUNT_DOC_BY_TITLE_SQL = "SELECT COUNT(1) FROM kb_document WHERE title = ?";

  private final List<KnowledgeDoc> docs = new CopyOnWriteArrayList<>();
  private final AtomicLong idGen = new AtomicLong(1);
  private final JdbcTemplate jdbcTemplate;
  private volatile boolean jdbcEnabled = true;

  public InMemoryKnowledgeService() {
    this((JdbcTemplate) null);
  }

  @Autowired
  public InMemoryKnowledgeService(
      ObjectProvider<JdbcTemplate> jdbcTemplateProvider,
      @Value("${hotel.jdbc.enabled:false}") boolean jdbcFeatureEnabled
  ) {
    this(jdbcFeatureEnabled ? jdbcTemplateProvider.getIfAvailable() : null);
  }

  public InMemoryKnowledgeService(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;

    addInMemoryDoc("投诉处理流程",
        "先致歉并记录信息，10分钟内响应，必要时提供换房或补偿，并完成回访。");
    addInMemoryDoc("夜间应急处理",
        "夜间出现噪音投诉时，先电话提醒，再上门协调，必要时升级值班经理处理。");
    addInMemoryDoc("客房异味处理",
        "确认异味来源后执行通风和深度清洁，无法快速处理时优先为客户换房。");
    addInMemoryDoc("前台高峰接待指引",
        "入住高峰时段实行双岗值守，优先处理预订已确认客户，并同步提示等候时长与房态变化。");
    addInMemoryDoc("早餐投诉补救规范",
        "针对早餐出餐慢、品类不足等投诉，应先致歉并记录房号，必要时发放补餐券并完成当班复盘。");
    addInMemoryDoc("换房处置流程",
        "若因噪音、异味、设备异常触发换房，应在确认房态后5分钟内完成方案说明、系统备注和房卡重制。");
    addInMemoryDoc("夜审交接清单",
        "夜审前需核对在住名单、未结订单、异常房态与次日团队预抵信息，形成交接记录供早班复核。");
    addInMemoryDoc("团体入住协调口径",
        "团队抵店前需核对房型分配、早餐批次、行李存放区与领队联系方式，前台统一使用团队接待口径。");
    addInMemoryDoc("差评闭环处理规范",
        "出现差评后应在24小时内完成原因归类、责任岗位确认、客户回访与改进措施登记。");
    addInMemoryDoc("房价策略调整建议",
        "当入住率持续高于80%且渠道需求上升时，可逐步上调高峰房型价格，并同步关注取消率变化。");
    addInMemoryDoc("周末排班建议",
        "周末与节假日前夜需增加前台和客房支援班次，重点保障高峰入住办理、布草周转和投诉响应速度。");
    addInMemoryDoc("会员复购提升建议",
        "对高频入住客户应关注房型偏好、安静需求与发票习惯，并在离店后推送回访和复购优惠信息。");
    addInMemoryDoc("深度清洁触发规则",
        "当连续两次出现异味、卫生或设施类投诉时，应触发深度清洁任务，并由值班经理确认复检结果。");

    bootstrapJdbc();
  }

  @Override
  public KnowledgeDoc addDoc(String title, String content) {
    if (useJdbc()) {
      try {
        LocalDateTime now = LocalDateTime.now();
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
          PreparedStatement ps = connection.prepareStatement(INSERT_DOC_SQL, Statement.RETURN_GENERATED_KEYS);
          ps.setString(1, title);
          ps.setString(2, content);
          ps.setString(3, "manual");
          ps.setTimestamp(4, Timestamp.valueOf(now));
          return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key != null) {
          return new KnowledgeDoc(key.longValue(), title, content, now);
        }
      } catch (DataAccessException ex) {
        jdbcEnabled = false;
        log.warn("JDBC addDoc failed, fallback to in-memory mode: {}", ex.getMessage());
      }
    }
    return addInMemoryDoc(title, content);
  }

  @Override
  public KnowledgeDoc updateDoc(long id, String title, String content) {
    if (useJdbc()) {
      try {
        int updated = jdbcTemplate.update(UPDATE_DOC_SQL, title, content, id);
        if (updated > 0) {
          return findJdbcDocById(id);
        }
      } catch (DataAccessException ex) {
        jdbcEnabled = false;
        log.warn("JDBC updateDoc failed, fallback to in-memory mode: {}", ex.getMessage());
      }
    }

    for (int i = 0; i < docs.size(); i++) {
      KnowledgeDoc existing = docs.get(i);
      if (existing.id() == id) {
        KnowledgeDoc updated = new KnowledgeDoc(id, title, content, existing.createdAt());
        docs.set(i, updated);
        return updated;
      }
    }
    return null;
  }

  @Override
  public boolean deleteDoc(long id) {
    if (useJdbc()) {
      try {
        return jdbcTemplate.update(DELETE_DOC_SQL, id) > 0;
      } catch (DataAccessException ex) {
        jdbcEnabled = false;
        log.warn("JDBC deleteDoc failed, fallback to in-memory mode: {}", ex.getMessage());
      }
    }

    return docs.removeIf(doc -> doc.id() == id);
  }

  @Override
  public List<KnowledgeDoc> listDocs() {
    if (useJdbc()) {
      try {
        return jdbcTemplate.query(SELECT_ALL_DOCS_SQL, (rs, rowNum) -> new KnowledgeDoc(
            rs.getLong("id"),
            rs.getString("title"),
            rs.getString("content"),
            rs.getTimestamp("created_at").toLocalDateTime()
        ));
      } catch (DataAccessException ex) {
        jdbcEnabled = false;
        log.warn("JDBC listDocs failed, fallback to in-memory mode: {}", ex.getMessage());
      }
    }
    return new ArrayList<>(docs);
  }

  @Override
  public List<KnowledgeDoc> search(String query, int topK) {
    Set<String> queryTokens = tokenize(query);
    return listDocs().stream()
        .map(doc -> new ScoredDoc(doc, score(queryTokens, doc)))
        .sorted(Comparator.comparingInt(ScoredDoc::score).reversed())
        .filter(item -> item.score > 0)
        .limit(topK)
        .map(ScoredDoc::doc)
        .toList();
  }

  private KnowledgeDoc addInMemoryDoc(String title, String content) {
    KnowledgeDoc doc = new KnowledgeDoc(
        idGen.getAndIncrement(),
        title,
        content,
        LocalDateTime.now()
    );
    docs.add(doc);
    return doc;
  }

  private KnowledgeDoc findJdbcDocById(long id) {
    try {
      List<KnowledgeDoc> result = jdbcTemplate.query(SELECT_DOC_BY_ID_SQL, (rs, rowNum) -> new KnowledgeDoc(
          rs.getLong("id"),
          rs.getString("title"),
          rs.getString("content"),
          rs.getTimestamp("created_at").toLocalDateTime()
      ), id);
      return result.isEmpty() ? null : result.get(0);
    } catch (DataAccessException ex) {
      jdbcEnabled = false;
      log.warn("JDBC findDocById failed, fallback to in-memory mode: {}", ex.getMessage());
      return null;
    }
  }

  private int score(Set<String> queryTokens, KnowledgeDoc doc) {
    Set<String> docTokens = tokenize(doc.title() + " " + doc.content());
    String raw = (doc.title() + " " + doc.content()).toLowerCase(Locale.ROOT);
    int hits = 0;
    for (String token : queryTokens) {
      if (docTokens.contains(token) || raw.contains(token)) {
        hits++;
      }
    }
    return hits;
  }

  private Set<String> tokenize(String text) {
    String normalized = text.toLowerCase(Locale.ROOT).replaceAll("[^\\p{L}\\p{N}]+", " ");
    Set<String> set = new HashSet<>();
    for (String token : normalized.split("\\s+")) {
      if (!token.isBlank()) {
        set.add(token);
      }
    }
    return set;
  }

  private void bootstrapJdbc() {
    if (!useJdbc()) {
      return;
    }
    try {
      jdbcTemplate.execute(CREATE_DOC_TABLE_SQL);
      upsertSeedDoc("投诉处理流程",
          "先致歉并记录信息，10分钟内响应，必要时提供换房或补偿，并完成回访。");
      upsertSeedDoc("夜间应急处理",
          "夜间出现噪音投诉时，先电话提醒，再上门协调，必要时升级值班经理处理。");
      upsertSeedDoc("客房异味处理",
          "确认异味来源后执行通风和深度清洁，无法快速处理时优先为客户换房。");
      upsertSeedDoc("前台高峰接待指引",
          "入住高峰时段实行双岗值守，优先处理预订已确认客户，并同步提示等候时长与房态变化。");
      upsertSeedDoc("早餐投诉补救规范",
          "针对早餐出餐慢、品类不足等投诉，应先致歉并记录房号，必要时发放补餐券并完成当班复盘。");
      upsertSeedDoc("换房处置流程",
          "若因噪音、异味、设备异常触发换房，应在确认房态后5分钟内完成方案说明、系统备注和房卡重制。");
      upsertSeedDoc("夜审交接清单",
          "夜审前需核对在住名单、未结订单、异常房态与次日团队预抵信息，形成交接记录供早班复核。");
      upsertSeedDoc("团体入住协调口径",
          "团队抵店前需核对房型分配、早餐批次、行李存放区与领队联系方式，前台统一使用团队接待口径。");
      upsertSeedDoc("差评闭环处理规范",
          "出现差评后应在24小时内完成原因归类、责任岗位确认、客户回访与改进措施登记。");
      upsertSeedDoc("房价策略调整建议",
          "当入住率持续高于80%且渠道需求上升时，可逐步上调高峰房型价格，并同步关注取消率变化。");
      upsertSeedDoc("周末排班建议",
          "周末与节假日前夜需增加前台和客房支援班次，重点保障高峰入住办理、布草周转和投诉响应速度。");
      upsertSeedDoc("会员复购提升建议",
          "对高频入住客户应关注房型偏好、安静需求与发票习惯，并在离店后推送回访和复购优惠信息。");
      upsertSeedDoc("深度清洁触发规则",
          "当连续两次出现异味、卫生或设施类投诉时，应触发深度清洁任务，并由值班经理确认复检结果。");
    } catch (DataAccessException ex) {
      jdbcEnabled = false;
      log.warn("JDBC bootstrap for knowledge docs failed: {}", ex.getMessage());
    }
  }

  private void upsertSeedDoc(String title, String content) {
    Integer count = jdbcTemplate.queryForObject(COUNT_DOC_BY_TITLE_SQL, Integer.class, title);
    if (count != null && count > 0) {
      return;
    }
    jdbcTemplate.update(
        INSERT_DOC_SQL,
        title,
        content,
        "seed",
        Timestamp.valueOf(LocalDateTime.now().minusDays(2))
    );
  }

  private boolean useJdbc() {
    return jdbcTemplate != null && jdbcEnabled;
  }

  private record ScoredDoc(KnowledgeDoc doc, int score) {}
}
