package com.hotel.ops.service;

import com.hotel.ops.dto.LoginResult;
import com.hotel.ops.dto.UserSummary;
import com.hotel.ops.model.AuthSession;
import java.util.List;
import java.util.Map;

public interface AuthService {

  LoginResult login(String username, String password);

  LoginResult register(String displayName, String username, String password);

  UserSummary currentUser(String token);

  List<UserSummary> listUsers();

  UserSummary createUser(String displayName, String username, String password, String role);

  UserSummary updateUserRole(long userId, String role);

  UserSummary updateUserStatus(long userId, String status);

  Map<String, Object> adminOverview();

  Map<String, List<String>> permissionMatrix();

  AuthSession getSession(String token);

  boolean isValidToken(String token);

  void requireAdmin(String token);

  UserSummary updateDisplayName(String token, String newDisplayName);

  void updatePassword(String token, String oldPassword, String newPassword);
}
