package com.hotel.ops.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.hotel.ops.common.AppException;
import com.hotel.ops.dto.LoginResult;
import com.hotel.ops.dto.UserSummary;
import java.util.Map;
import org.junit.jupiter.api.Test;

class AuthServiceImplTest {

  private final AuthServiceImpl authService = new AuthServiceImpl();

  @Test
  void registerShouldCreateStaffAndAllowLogin() {
    LoginResult result = authService.register("测试员工", "demo_user", "demo123");

    assertEquals("demo_user", result.username());
    assertEquals("STAFF", result.role());
    assertEquals("测试员工", result.displayName());
    assertNotNull(result.token());
    assertEquals(3, result.token().split("\\.").length);
  }

  @Test
  void adminShouldCreateManagerUser() {
    UserSummary created = authService.createUser("夜班经理", "night_manager", "manager666", "MANAGER");

    assertEquals("MANAGER", created.role());
    assertEquals("ACTIVE", created.status());
  }

  @Test
  void disabledUserShouldNotLogin() {
    UserSummary created = authService.createUser("临时员工", "temp_staff", "temp1234", "STAFF");
    authService.updateUserStatus(created.id(), "DISABLED");

    assertThrows(AppException.class, () -> authService.login("temp_staff", "temp1234"));
  }

  @Test
  void createUserShouldRejectDuplicateUsername() {
    authService.createUser("客服A", "dup_user", "dup12345", "STAFF");
    assertThrows(AppException.class, () -> authService.createUser("客服B", "dup_user", "dup12345", "STAFF"));
  }

  @Test
  void updateRoleShouldTakeEffect() {
    UserSummary created = authService.createUser("值班主管", "duty_lead", "lead1234", "STAFF");
    UserSummary updated = authService.updateUserRole(created.id(), "MANAGER");

    assertEquals("MANAGER", updated.role());
  }

  @Test
  void updateStatusShouldRejectInvalidStatus() {
    UserSummary created = authService.createUser("前台B", "front_b", "front123", "STAFF");
    assertThrows(AppException.class, () -> authService.updateUserStatus(created.id(), "UNKNOWN"));
  }

  @Test
  void createUserShouldRejectInvalidRole() {
    assertThrows(AppException.class, () -> authService.createUser("测试", "invalid_role", "abc12345", "OWNER"));
  }

  @Test
  void listUsersShouldContainSeedUsers() {
    var users = authService.listUsers();
    assertTrue(users.stream().anyMatch(u -> "admin".equals(u.username())));
    assertTrue(users.stream().anyMatch(u -> "manager".equals(u.username())));
    assertTrue(users.stream().anyMatch(u -> "staff".equals(u.username())));
  }

  @Test
  void adminOverviewShouldReturnRoleCounts() {
    Map<String, Object> overview = authService.adminOverview();
    assertTrue(((Number) overview.get("permissionRoles")).intValue() >= 3);
    assertTrue(((Number) overview.get("totalUsers")).intValue() >= 3);
  }
}
