package com.hotel.ops.service.impl;

import com.hotel.ops.common.AppException;
import com.hotel.ops.dto.LoginResult;
import com.hotel.ops.dto.UserSummary;
import com.hotel.ops.model.AuthSession;
import com.hotel.ops.model.UserAccount;
import com.hotel.ops.service.AuthService;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
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
public class AuthServiceImpl implements AuthService {

  private static final Logger log = LoggerFactory.getLogger(AuthServiceImpl.class);
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
  private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};
  private static final Base64.Encoder JWT_ENCODER = Base64.getUrlEncoder().withoutPadding();
  private static final Base64.Decoder JWT_DECODER = Base64.getUrlDecoder();
  private static final String DEFAULT_JWT_SECRET =
      "hotel-ops-demo-secret-change-me-hotel-ops-demo-secret";

  private static final long TOKEN_TTL_SECONDS = 60L * 60L * 8L;
  private static final List<String> VALID_ROLES = List.of("ADMIN", "MANAGER", "STAFF");
  private static final List<String> VALID_STATUS = List.of("ACTIVE", "DISABLED");
  private static final Map<String, List<String>> PERMISSION_MATRIX = Map.of(
      "ADMIN", List.of("用户管理", "角色调整", "账号启停", "知识维护", "智能问答", "经营总览", "预测分析"),
      "MANAGER", List.of("知识维护", "智能问答", "经营总览", "预测分析"),
      "STAFF", List.of("智能问答", "经营总览")
  );

  private static final String CREATE_USER_TABLE_SQL = """
      CREATE TABLE IF NOT EXISTS sys_user (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(64) NOT NULL UNIQUE,
        display_name VARCHAR(64) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role_code VARCHAR(32) NOT NULL,
        status TINYINT NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      )
      """;

  private static final String UPSERT_DEMO_USER_SQL = """
      INSERT INTO sys_user (username, display_name, password_hash, role_code, status, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
      ON DUPLICATE KEY UPDATE
      display_name = VALUES(display_name),
      password_hash = VALUES(password_hash),
      role_code = VALUES(role_code),
      status = VALUES(status)
      """;

  private static final String SELECT_USER_BY_USERNAME_SQL = """
      SELECT id, username, display_name, password_hash, role_code, status, created_at
      FROM sys_user
      WHERE username = ?
      """;

  private static final String SELECT_USER_BY_ID_SQL = """
      SELECT id, username, display_name, password_hash, role_code, status, created_at
      FROM sys_user
      WHERE id = ?
      """;

  private static final String SELECT_ALL_USERS_SQL = """
      SELECT id, username, display_name, password_hash, role_code, status, created_at
      FROM sys_user
      ORDER BY id
      """;

  private static final String INSERT_USER_SQL = """
      INSERT INTO sys_user (username, display_name, password_hash, role_code, status, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
      """;

  private static final String UPDATE_ROLE_SQL = "UPDATE sys_user SET role_code = ? WHERE id = ?";
  private static final String UPDATE_STATUS_SQL = "UPDATE sys_user SET status = ? WHERE id = ?";
  private static final String UPDATE_DISPLAY_NAME_SQL = "UPDATE sys_user SET display_name = ? WHERE id = ?";
  private static final String UPDATE_PASSWORD_SQL = "UPDATE sys_user SET password_hash = ? WHERE id = ?";
  private static final String COUNT_USERNAME_SQL = "SELECT COUNT(1) FROM sys_user WHERE username = ?";

  private final Map<String, UserRecord> usersByUsername = new ConcurrentHashMap<>();
  private final Map<Long, String> usernameById = new ConcurrentHashMap<>();
  private final AtomicLong userIdGen = new AtomicLong(1000);
  private final JdbcTemplate jdbcTemplate;
  private final byte[] jwtSecretBytes;
  private final long jwtTtlSeconds;
  private volatile boolean jdbcEnabled = true;

  public AuthServiceImpl() {
    this(null, DEFAULT_JWT_SECRET, TOKEN_TTL_SECONDS);
  }

  @Autowired
  public AuthServiceImpl(
      ObjectProvider<JdbcTemplate> jdbcTemplateProvider,
      @Value("${hotel.jdbc.enabled:false}") boolean jdbcFeatureEnabled,
      @Value("${hotel.auth.jwt-secret:" + DEFAULT_JWT_SECRET + "}") String jwtSecret,
      @Value("${hotel.auth.jwt-expire-seconds:" + TOKEN_TTL_SECONDS + "}") long jwtExpireSeconds
  ) {
    this(jdbcFeatureEnabled ? jdbcTemplateProvider.getIfAvailable() : null, jwtSecret, jwtExpireSeconds);
  }

  public AuthServiceImpl(JdbcTemplate jdbcTemplate) {
    this(jdbcTemplate, DEFAULT_JWT_SECRET, TOKEN_TTL_SECONDS);
  }

  public AuthServiceImpl(JdbcTemplate jdbcTemplate, String jwtSecret, long jwtExpireSeconds) {
    this.jdbcTemplate = jdbcTemplate;
    this.jwtSecretBytes = normalizeJwtSecret(jwtSecret);
    this.jwtTtlSeconds = jwtExpireSeconds > 0 ? jwtExpireSeconds : TOKEN_TTL_SECONDS;
    seedUser("系统管理员", "admin", "admin123", "ADMIN");
    seedUser("值班经理", "manager", "manager123", "MANAGER");
    seedUser("普通员工", "staff", "staff123", "STAFF");
    seedUser("前台主管", "frontlead", "front123", "MANAGER");
    seedUser("收益分析师", "revenue", "revenue123", "MANAGER");
    seedUser("客房主管", "housekeep", "house123", "STAFF");
    seedUser("质检专员", "quality", "quality123", "STAFF");
    seedUser("夜审专员", "nightaudit", "night123", "STAFF");
    bootstrapJdbc();
  }

  @Override
  public LoginResult login(String username, String password) {
    String normalizedUsername = normalizeUsername(username);
    if (useJdbc()) {
      try {
        UserDbRecord user = findDbUserByUsername(normalizedUsername);
        if (user == null || !user.passwordHash().equals(password)) {
          throw new AppException(401, "用户名或密码错误");
        }
        if (!"ACTIVE".equals(user.status())) {
          throw new AppException(403, "当前账号已被停用");
        }
        return issueToken(user.id(), user.username(), user.displayName(), user.role());
      } catch (DataAccessException ex) {
        logJdbcFallback("login", ex);
      }
    }

    UserRecord user = usersByUsername.get(normalizedUsername);
    if (user == null || !user.password().equals(password)) {
      throw new AppException(401, "用户名或密码错误");
    }
    if (!"ACTIVE".equals(user.account().status())) {
      throw new AppException(403, "当前账号已被停用");
    }
    return issueToken(
        user.account().id(),
        user.account().username(),
        user.account().displayName(),
        user.account().role()
    );
  }

  @Override
  public LoginResult register(String displayName, String username, String password) {
    UserSummary user = createUser(displayName, username, password, "STAFF");
    return login(user.username(), password);
  }

  @Override
  public UserSummary currentUser(String token) {
    AuthSession session = getSession(token);
    if (session == null) {
      throw new AppException(401, "未登录或登录已过期");
    }

    if (useJdbc()) {
      try {
        UserDbRecord user = findDbUserById(session.userId());
        if (user == null) {
          throw new AppException(404, "用户不存在");
        }
        return toSummary(user);
      } catch (DataAccessException ex) {
        logJdbcFallback("currentUser", ex);
      }
    }

    return toSummary(findUserById(session.userId()).account());
  }

  @Override
  public List<UserSummary> listUsers() {
    if (useJdbc()) {
      try {
        return jdbcTemplate.query(SELECT_ALL_USERS_SQL, (rs, rowNum) -> new UserDbRecord(
            rs.getLong("id"),
            rs.getString("username"),
            rs.getString("display_name"),
            rs.getString("password_hash"),
            normalizeRole(rs.getString("role_code")),
            toStatus(rs.getInt("status")),
            rs.getTimestamp("created_at").toLocalDateTime()
        )).stream().map(this::toSummary).toList();
      } catch (DataAccessException ex) {
        logJdbcFallback("listUsers", ex);
      }
    }

    return usersByUsername.values().stream()
        .map(UserRecord::account)
        .sorted(Comparator.comparingLong(UserAccount::id))
        .map(this::toSummary)
        .toList();
  }

  @Override
  public UserSummary createUser(String displayName, String username, String password, String role) {
    String normalizedUsername = normalizeUsername(username);
    String normalizedRole = normalizeRole(role);
    if (password == null || password.isBlank()) {
      throw new AppException(400, "密码不能为空");
    }
    String normalizedDisplayName = normalizeDisplayName(displayName, normalizedUsername);

    if (useJdbc()) {
      try {
        Integer existingCount = jdbcTemplate.queryForObject(
            COUNT_USERNAME_SQL, Integer.class, normalizedUsername
        );
        if (existingCount != null && existingCount > 0) {
          throw new AppException(409, "用户名已存在");
        }
        LocalDateTime now = LocalDateTime.now();
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbcTemplate.update(connection -> {
          PreparedStatement ps = connection.prepareStatement(INSERT_USER_SQL, Statement.RETURN_GENERATED_KEYS);
          ps.setString(1, normalizedUsername);
          ps.setString(2, normalizedDisplayName);
          ps.setString(3, password);
          ps.setString(4, normalizedRole);
          ps.setInt(5, 1);
          ps.setTimestamp(6, Timestamp.valueOf(now));
          return ps;
        }, keyHolder);
        Number userId = keyHolder.getKey();
        if (userId == null) {
          throw new AppException(500, "创建用户失败");
        }
        UserDbRecord created = new UserDbRecord(
            userId.longValue(), normalizedUsername, normalizedDisplayName,
            password, normalizedRole, "ACTIVE", now
        );
        return toSummary(created);
      } catch (DataAccessException ex) {
        logJdbcFallback("createUser", ex);
      }
    }

    if (usersByUsername.containsKey(normalizedUsername)) {
      throw new AppException(409, "用户名已存在");
    }
    long userId = userIdGen.incrementAndGet();
    UserAccount account = new UserAccount(
        userId,
        normalizedUsername,
        normalizedDisplayName,
        normalizedRole,
        "ACTIVE",
        LocalDateTime.now()
    );
    usersByUsername.put(normalizedUsername, new UserRecord(account, password));
    usernameById.put(userId, normalizedUsername);
    return toSummary(account);
  }

  @Override
  public UserSummary updateUserRole(long userId, String role) {
    String normalizedRole = normalizeRole(role);
    if (useJdbc()) {
      try {
        UserDbRecord existing = findDbUserById(userId);
        if (existing == null) {
          throw new AppException(404, "用户不存在");
        }
        int updated = jdbcTemplate.update(UPDATE_ROLE_SQL, normalizedRole, userId);
        if (updated <= 0) {
          throw new AppException(404, "用户不存在");
        }
        UserDbRecord refreshed = findDbUserById(userId);
        if (refreshed == null) {
          throw new AppException(404, "用户不存在");
        }
        refreshUserSessions(refreshed.username());
        return toSummary(refreshed);
      } catch (DataAccessException ex) {
        logJdbcFallback("updateUserRole", ex);
      }
    }

    UserRecord existing = findUserById(userId);
    UserAccount updatedAccount = new UserAccount(
        existing.account().id(),
        existing.account().username(),
        existing.account().displayName(),
        normalizedRole,
        existing.account().status(),
        existing.account().createdAt()
    );
    usersByUsername.put(existing.account().username(), new UserRecord(updatedAccount, existing.password()));
    refreshUserSessions(updatedAccount.username());
    return toSummary(updatedAccount);
  }

  @Override
  public UserSummary updateUserStatus(long userId, String status) {
    String normalizedStatus = normalizeStatus(status);
    if (useJdbc()) {
      try {
        UserDbRecord existing = findDbUserById(userId);
        if (existing == null) {
          throw new AppException(404, "用户不存在");
        }
        int updated = jdbcTemplate.update(UPDATE_STATUS_SQL, toStatusCode(normalizedStatus), userId);
        if (updated <= 0) {
          throw new AppException(404, "用户不存在");
        }
        UserDbRecord refreshed = findDbUserById(userId);
        if (refreshed == null) {
          throw new AppException(404, "用户不存在");
        }
        refreshUserSessions(refreshed.username());
        return toSummary(refreshed);
      } catch (DataAccessException ex) {
        logJdbcFallback("updateUserStatus", ex);
      }
    }

    UserRecord existing = findUserById(userId);
    UserAccount updatedAccount = new UserAccount(
        existing.account().id(),
        existing.account().username(),
        existing.account().displayName(),
        existing.account().role(),
        normalizedStatus,
        existing.account().createdAt()
    );
    usersByUsername.put(existing.account().username(), new UserRecord(updatedAccount, existing.password()));
    refreshUserSessions(updatedAccount.username());
    return toSummary(updatedAccount);
  }

  @Override
  public Map<String, Object> adminOverview() {
    List<UserSummary> users = listUsers();
    long activeCount = users.stream().filter(user -> "ACTIVE".equals(user.status())).count();
    long disabledCount = users.size() - activeCount;
    Map<String, Long> roleCounts = new LinkedHashMap<>();
    for (String role : VALID_ROLES) {
      roleCounts.put(role, users.stream().filter(user -> role.equals(user.role())).count());
    }
    return Map.of(
        "totalUsers", users.size(),
        "activeUsers", activeCount,
        "disabledUsers", disabledCount,
        "roleCounts", roleCounts,
        "permissionRoles", VALID_ROLES.size()
    );
  }

  @Override
  public Map<String, List<String>> permissionMatrix() {
    return PERMISSION_MATRIX;
  }

  @Override
  public AuthSession getSession(String token) {
    if (token == null || token.isBlank()) {
      return null;
    }
    JwtClaims claims = parseJwt(token);
    if (claims == null || Instant.now().getEpochSecond() >= claims.expireAt()) {
      return null;
    }

    if (useJdbc()) {
      try {
        UserDbRecord user = findDbUserById(claims.userId());
        if (user == null || !"ACTIVE".equals(user.status())) {
          return null;
        }
        if (!user.username().equals(claims.username())) {
          return null;
        }
        return new AuthSession(user.id(), user.username(), user.displayName(), user.role());
      } catch (DataAccessException ex) {
        logJdbcFallback("getSession", ex);
      }
    }

    UserRecord user = usersByUsername.get(claims.username());
    if (user == null || user.account().id() != claims.userId()
        || !"ACTIVE".equals(user.account().status())) {
      return null;
    }
    return new AuthSession(
        user.account().id(),
        user.account().username(),
        user.account().displayName(),
        user.account().role()
    );
  }

  @Override
  public boolean isValidToken(String token) {
    return getSession(token) != null;
  }

  @Override
  public void requireAdmin(String token) {
    AuthSession session = getSession(token);
    if (session == null) {
      throw new AppException(401, "未登录或登录已过期");
    }
    if (!"ADMIN".equals(session.role())) {
      throw new AppException(403, "当前账号无管理员权限");
    }
  }

  @Override
  public UserSummary updateDisplayName(String token, String newDisplayName) {
    AuthSession session = getSession(token);
    if (session == null) {
      throw new AppException(401, "未登录或登录已过期");
    }
    if (newDisplayName == null || newDisplayName.isBlank()) {
      throw new AppException(400, "显示名称不能为空");
    }
    String trimmedName = newDisplayName.trim();

    if (useJdbc()) {
      try {
        int updated = jdbcTemplate.update(UPDATE_DISPLAY_NAME_SQL, trimmedName, session.userId());
        if (updated <= 0) {
          throw new AppException(404, "用户不存在");
        }
        UserDbRecord refreshed = findDbUserById(session.userId());
        if (refreshed == null) {
          throw new AppException(404, "用户不存在");
        }
        return toSummary(refreshed);
      } catch (DataAccessException ex) {
        logJdbcFallback("updateDisplayName", ex);
      }
    }

    UserRecord existing = findUserById(session.userId());
    UserAccount updatedAccount = new UserAccount(
        existing.account().id(),
        existing.account().username(),
        trimmedName,
        existing.account().role(),
        existing.account().status(),
        existing.account().createdAt()
    );
    usersByUsername.put(existing.account().username(), new UserRecord(updatedAccount, existing.password()));
    return toSummary(updatedAccount);
  }

  @Override
  public void updatePassword(String token, String oldPassword, String newPassword) {
    AuthSession session = getSession(token);
    if (session == null) {
      throw new AppException(401, "未登录或登录已过期");
    }
    if (oldPassword == null || oldPassword.isBlank()) {
      throw new AppException(400, "旧密码不能为空");
    }
    if (newPassword == null || newPassword.isBlank()) {
      throw new AppException(400, "新密码不能为空");
    }
    if (newPassword.length() < 6) {
      throw new AppException(400, "新密码长度不能少于6位");
    }

    if (useJdbc()) {
      try {
        UserDbRecord user = findDbUserById(session.userId());
        if (user == null) {
          throw new AppException(404, "用户不存在");
        }
        if (!user.passwordHash().equals(oldPassword)) {
          throw new AppException(400, "旧密码不正确");
        }
        jdbcTemplate.update(UPDATE_PASSWORD_SQL, newPassword, session.userId());
        return;
      } catch (DataAccessException ex) {
        logJdbcFallback("updatePassword", ex);
      }
    }

    UserRecord existing = findUserById(session.userId());
    if (!existing.password().equals(oldPassword)) {
      throw new AppException(400, "旧密码不正确");
    }
    usersByUsername.put(existing.account().username(), new UserRecord(existing.account(), newPassword));
  }

  private LoginResult issueToken(long userId, String username, String displayName, String role) {
    String token = generateJwt(userId, username, displayName, role);
    return new LoginResult(token, username, displayName, role);
  }

  private void bootstrapJdbc() {
    if (!useJdbc()) {
      return;
    }
    try {
      jdbcTemplate.execute(CREATE_USER_TABLE_SQL);
      upsertDemoUser("admin", "系统管理员", "admin123", "ADMIN");
      upsertDemoUser("manager", "值班经理", "manager123", "MANAGER");
      upsertDemoUser("staff", "普通员工", "staff123", "STAFF");
      upsertDemoUser("frontlead", "前台主管", "front123", "MANAGER");
      upsertDemoUser("revenue", "收益分析师", "revenue123", "MANAGER");
      upsertDemoUser("housekeep", "客房主管", "house123", "STAFF");
      upsertDemoUser("quality", "质检专员", "quality123", "STAFF");
      upsertDemoUser("nightaudit", "夜审专员", "night123", "STAFF");
    } catch (DataAccessException ex) {
      logJdbcFallback("bootstrapJdbc", ex);
    }
  }

  private void upsertDemoUser(String username, String displayName, String password, String role) {
    jdbcTemplate.update(
        UPSERT_DEMO_USER_SQL,
        username,
        displayName,
        password,
        role,
        1,
        Timestamp.valueOf(LocalDateTime.now().minusDays(3))
    );
  }

  private UserDbRecord findDbUserByUsername(String username) {
    List<UserDbRecord> users = jdbcTemplate.query(
        SELECT_USER_BY_USERNAME_SQL,
        (rs, rowNum) -> new UserDbRecord(
            rs.getLong("id"),
            rs.getString("username"),
            rs.getString("display_name"),
            rs.getString("password_hash"),
            normalizeRole(rs.getString("role_code")),
            toStatus(rs.getInt("status")),
            rs.getTimestamp("created_at").toLocalDateTime()
        ),
        username
    );
    return users.isEmpty() ? null : users.get(0);
  }

  private UserDbRecord findDbUserById(long userId) {
    List<UserDbRecord> users = jdbcTemplate.query(
        SELECT_USER_BY_ID_SQL,
        (rs, rowNum) -> new UserDbRecord(
            rs.getLong("id"),
            rs.getString("username"),
            rs.getString("display_name"),
            rs.getString("password_hash"),
            normalizeRole(rs.getString("role_code")),
            toStatus(rs.getInt("status")),
            rs.getTimestamp("created_at").toLocalDateTime()
        ),
        userId
    );
    return users.isEmpty() ? null : users.get(0);
  }

  private void seedUser(String displayName, String username, String password, String role) {
    String normalizedUsername = normalizeUsername(username);
    long userId = userIdGen.incrementAndGet();
    UserAccount account = new UserAccount(
        userId,
        normalizedUsername,
        displayName,
        role,
        "ACTIVE",
        LocalDateTime.now().minusDays(3)
    );
    usersByUsername.put(normalizedUsername, new UserRecord(account, password));
    usernameById.put(userId, normalizedUsername);
  }

  private UserRecord findUserById(long userId) {
    String username = usernameById.get(userId);
    if (username == null) {
      throw new AppException(404, "用户不存在");
    }
    UserRecord record = usersByUsername.get(username);
    if (record == null) {
      throw new AppException(404, "用户不存在");
    }
    return record;
  }

  private void refreshUserSessions(String username) {
    // JWT 为无状态令牌，账号状态与角色变更通过 getSession() 的实时用户查询生效。
  }

  private UserSummary toSummary(UserAccount account) {
    return new UserSummary(
        account.id(),
        account.username(),
        account.displayName(),
        account.role(),
        account.status(),
        account.createdAt()
    );
  }

  private UserSummary toSummary(UserDbRecord account) {
    return new UserSummary(
        account.id(),
        account.username(),
        account.displayName(),
        account.role(),
        account.status(),
        account.createdAt()
    );
  }

  private String normalizeUsername(String username) {
    if (username == null || username.isBlank()) {
      throw new AppException(400, "用户名不能为空");
    }
    return username.trim().toLowerCase(Locale.ROOT);
  }

  private String normalizeDisplayName(String displayName, String fallback) {
    if (displayName == null || displayName.isBlank()) {
      return fallback;
    }
    return displayName.trim();
  }

  private String normalizeRole(String role) {
    String normalizedRole = role == null ? "" : role.trim().toUpperCase(Locale.ROOT);
    if (!VALID_ROLES.contains(normalizedRole)) {
      throw new AppException(400, "角色仅支持 ADMIN、MANAGER、STAFF");
    }
    return normalizedRole;
  }

  private String normalizeStatus(String status) {
    String normalizedStatus = status == null ? "" : status.trim().toUpperCase(Locale.ROOT);
    if (!VALID_STATUS.contains(normalizedStatus)) {
      throw new AppException(400, "状态仅支持 ACTIVE、DISABLED");
    }
    return normalizedStatus;
  }

  private int toStatusCode(String status) {
    return "ACTIVE".equals(status) ? 1 : 0;
  }

  private String toStatus(int statusCode) {
    return statusCode == 1 ? "ACTIVE" : "DISABLED";
  }

  private boolean useJdbc() {
    return jdbcTemplate != null && jdbcEnabled;
  }

  private void logJdbcFallback(String action, Exception ex) {
    jdbcEnabled = false;
    log.warn("JDBC {} failed, fallback to in-memory mode: {}", action, ex.getMessage());
  }

  private byte[] normalizeJwtSecret(String jwtSecret) {
    String secret = jwtSecret == null || jwtSecret.isBlank() ? DEFAULT_JWT_SECRET : jwtSecret.trim();
    return secret.getBytes(StandardCharsets.UTF_8);
  }

  private String generateJwt(long userId, String username, String displayName, String role) {
    long now = Instant.now().getEpochSecond();
    long expireAt = now + jwtTtlSeconds;
    Map<String, Object> header = Map.of("alg", "HS256", "typ", "JWT");
    Map<String, Object> payload = new HashMap<>();
    payload.put("sub", username);
    payload.put("uid", userId);
    payload.put("displayName", displayName);
    payload.put("role", role);
    payload.put("iat", now);
    payload.put("exp", expireAt);

    String headerSegment = encodeSegment(header);
    String payloadSegment = encodeSegment(payload);
    String content = headerSegment + "." + payloadSegment;
    return content + "." + sign(content);
  }

  private JwtClaims parseJwt(String token) {
    try {
      String[] segments = token.split("\\.");
      if (segments.length != 3) {
        return null;
      }
      String content = segments[0] + "." + segments[1];
      String expectedSignature = sign(content);
      if (!MessageDigest.isEqual(
          expectedSignature.getBytes(StandardCharsets.UTF_8),
          segments[2].getBytes(StandardCharsets.UTF_8)
      )) {
        return null;
      }

      Map<String, Object> header = decodeSegment(segments[0]);
      if (!"HS256".equals(String.valueOf(header.get("alg")))) {
        return null;
      }

      Map<String, Object> payload = decodeSegment(segments[1]);
      long userId = parseLongClaim(payload.get("uid"));
      long expireAt = parseLongClaim(payload.get("exp"));
      String username = String.valueOf(payload.getOrDefault("sub", "")).trim().toLowerCase(Locale.ROOT);
      if (userId <= 0 || expireAt <= 0 || username.isBlank()) {
        return null;
      }
      return new JwtClaims(userId, username, expireAt);
    } catch (Exception ex) {
      return null;
    }
  }

  private String encodeSegment(Map<String, Object> content) {
    try {
      byte[] json = OBJECT_MAPPER.writeValueAsBytes(content);
      return JWT_ENCODER.encodeToString(json);
    } catch (Exception ex) {
      throw new IllegalStateException("JWT 编码失败", ex);
    }
  }

  private Map<String, Object> decodeSegment(String segment) {
    try {
      byte[] json = JWT_DECODER.decode(segment);
      return OBJECT_MAPPER.readValue(json, MAP_TYPE);
    } catch (Exception ex) {
      throw new IllegalStateException("JWT 解码失败", ex);
    }
  }

  private String sign(String content) {
    try {
      Mac mac = Mac.getInstance("HmacSHA256");
      mac.init(new SecretKeySpec(jwtSecretBytes, "HmacSHA256"));
      return JWT_ENCODER.encodeToString(mac.doFinal(content.getBytes(StandardCharsets.UTF_8)));
    } catch (GeneralSecurityException ex) {
      throw new IllegalStateException("JWT 签名失败", ex);
    }
  }

  private long parseLongClaim(Object value) {
    if (value instanceof Number number) {
      return number.longValue();
    }
    if (value == null) {
      return -1;
    }
    try {
      return Long.parseLong(String.valueOf(value));
    } catch (NumberFormatException ex) {
      return -1;
    }
  }

  private record UserRecord(UserAccount account, String password) {}

  private record UserDbRecord(
      long id,
      String username,
      String displayName,
      String passwordHash,
      String role,
      String status,
      LocalDateTime createdAt
  ) {}

  private record JwtClaims(long userId, String username, long expireAt) {}
}
