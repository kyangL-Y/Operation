package com.hotel.ops.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.hotel.ops.common.AppException;
import com.hotel.ops.dto.LoginResult;
import com.hotel.ops.dto.UserSummary;
import com.hotel.ops.service.impl.AuthServiceImpl;
import org.junit.jupiter.api.Test;

class AuthServiceImplTest {

  private final AuthServiceImpl service = new AuthServiceImpl();

  @Test
  void should_login_success_and_validate_token() {
    LoginResult result = service.login("admin", "admin123");
    assertNotNull(result.token());
    assertEquals(3, result.token().split("\\.").length);
    assertTrue(service.isValidToken(result.token()));
    assertFalse(service.isValidToken("invalid-token"));
  }

  @Test
  void should_reject_invalid_password() {
    assertThrows(AppException.class, () -> service.login("admin", "wrong-password"));
  }

  @Test
  void should_require_admin_permission() {
    LoginResult admin = service.login("admin", "admin123");
    service.requireAdmin(admin.token());

    LoginResult staff = service.login("staff", "staff123");
    assertThrows(AppException.class, () -> service.requireAdmin(staff.token()));
  }

  @Test
  void should_return_current_user_profile() {
    LoginResult result = service.login("manager", "manager123");
    UserSummary current = service.currentUser(result.token());

    assertEquals("manager", current.username());
    assertEquals("MANAGER", current.role());
  }

  @Test
  void should_invalidate_session_after_user_disabled() {
    UserSummary created = service.createUser("巡检员", "inspector", "inspect123", "STAFF");
    LoginResult login = service.login("inspector", "inspect123");
    assertTrue(service.isValidToken(login.token()));

    service.updateUserStatus(created.id(), "DISABLED");
    assertFalse(service.isValidToken(login.token()));
  }
}
