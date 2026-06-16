package com.hotel.ops.config;

import com.hotel.ops.common.AppException;
import com.hotel.ops.model.AuthSession;
import com.hotel.ops.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class AuthInterceptor implements HandlerInterceptor {

  private final AuthService authService;

  public AuthInterceptor(AuthService authService) {
    this.authService = authService;
  }

  @Override
  public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
    if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
      return true;
    }
    String token = request.getHeader("X-Auth-Token");
    AuthSession session = authService.getSession(token);
    if (session == null) {
      throw new AppException(401, "未登录或登录已过期");
    }
    request.setAttribute("CURRENT_USER", session.username());
    request.setAttribute("CURRENT_ROLE", session.role());
    return true;
  }
}
