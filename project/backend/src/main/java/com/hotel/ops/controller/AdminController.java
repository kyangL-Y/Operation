package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.dto.UserCreateRequest;
import com.hotel.ops.dto.UserRoleUpdateRequest;
import com.hotel.ops.dto.UserStatusUpdateRequest;
import com.hotel.ops.dto.UserSummary;
import com.hotel.ops.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

  private final AuthService authService;

  public AdminController(AuthService authService) {
    this.authService = authService;
  }

  @GetMapping("/overview")
  public ApiResponse<Map<String, Object>> overview(HttpServletRequest request) {
    authService.requireAdmin(request.getHeader("X-Auth-Token"));
    return ApiResponse.ok(authService.adminOverview());
  }

  @GetMapping("/users")
  public ApiResponse<List<UserSummary>> listUsers(HttpServletRequest request) {
    authService.requireAdmin(request.getHeader("X-Auth-Token"));
    return ApiResponse.ok(authService.listUsers());
  }

  @PostMapping("/users")
  public ApiResponse<UserSummary> createUser(
      HttpServletRequest request,
      @Valid @RequestBody UserCreateRequest body
  ) {
    authService.requireAdmin(request.getHeader("X-Auth-Token"));
    return ApiResponse.ok(authService.createUser(
        body.displayName(),
        body.username(),
        body.password(),
        body.role()
    ));
  }

  @PutMapping("/users/{userId}/role")
  public ApiResponse<UserSummary> updateRole(
      HttpServletRequest request,
      @PathVariable("userId") long userId,
      @Valid @RequestBody UserRoleUpdateRequest body
  ) {
    authService.requireAdmin(request.getHeader("X-Auth-Token"));
    return ApiResponse.ok(authService.updateUserRole(userId, body.role()));
  }

  @PutMapping("/users/{userId}/status")
  public ApiResponse<UserSummary> updateStatus(
      HttpServletRequest request,
      @PathVariable("userId") long userId,
      @Valid @RequestBody UserStatusUpdateRequest body
  ) {
    authService.requireAdmin(request.getHeader("X-Auth-Token"));
    return ApiResponse.ok(authService.updateUserStatus(userId, body.status()));
  }

  @GetMapping("/permissions")
  public ApiResponse<Map<String, List<String>>> permissions(HttpServletRequest request) {
    authService.requireAdmin(request.getHeader("X-Auth-Token"));
    return ApiResponse.ok(authService.permissionMatrix());
  }
}
