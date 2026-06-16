package com.hotel.ops.controller;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.dto.LoginRequest;
import com.hotel.ops.dto.LoginResult;
import com.hotel.ops.dto.RegisterRequest;
import com.hotel.ops.dto.UpdatePasswordRequest;
import com.hotel.ops.dto.UpdateProfileRequest;
import com.hotel.ops.dto.UserSummary;
import com.hotel.ops.service.AuthService;
import jakarta.validation.Valid;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

  private final AuthService authService;

  public AuthController(AuthService authService) {
    this.authService = authService;
  }

  @PostMapping("/login")
  public ApiResponse<LoginResult> login(@Valid @RequestBody LoginRequest request) {
    return ApiResponse.ok(authService.login(request.username(), request.password()));
  }

  @PostMapping("/register")
  public ApiResponse<LoginResult> register(@Valid @RequestBody RegisterRequest request) {
    return ApiResponse.ok(authService.register(
        request.displayName(),
        request.username(),
        request.password()
    ));
  }

  @GetMapping("/me")
  public ApiResponse<UserSummary> currentUser(HttpServletRequest request) {
    return ApiResponse.ok(authService.currentUser(request.getHeader("X-Auth-Token")));
  }

  @PutMapping("/profile")
  public ApiResponse<UserSummary> updateProfile(
      HttpServletRequest request,
      @Valid @RequestBody UpdateProfileRequest body) {
    return ApiResponse.ok(authService.updateDisplayName(
        request.getHeader("X-Auth-Token"),
        body.displayName()
    ));
  }

  @PutMapping("/password")
  public ApiResponse<Void> updatePassword(
      HttpServletRequest request,
      @Valid @RequestBody UpdatePasswordRequest body) {
    authService.updatePassword(
        request.getHeader("X-Auth-Token"),
        body.oldPassword(),
        body.newPassword()
    );
    return ApiResponse.ok(null);
  }
}
