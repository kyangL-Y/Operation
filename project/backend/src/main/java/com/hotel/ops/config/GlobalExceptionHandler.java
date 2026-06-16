package com.hotel.ops.config;

import com.hotel.ops.common.ApiResponse;
import com.hotel.ops.common.AppException;
import jakarta.validation.ConstraintViolationException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

  private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

  @ExceptionHandler(AppException.class)
  public ApiResponse<Void> handleAppException(AppException ex) {
    return ApiResponse.fail(ex.code(), ex.getMessage());
  }

  @ExceptionHandler(MethodArgumentNotValidException.class)
  public ApiResponse<Void> handleInvalidArgument(MethodArgumentNotValidException ex) {
    FieldError firstError = ex.getBindingResult().getFieldErrors().stream().findFirst().orElse(null);
    String message = firstError == null ? "请求参数不合法" : firstError.getDefaultMessage();
    return ApiResponse.fail(400, message);
  }

  @ExceptionHandler({HttpMessageNotReadableException.class, ConstraintViolationException.class})
  public ApiResponse<Void> handleReadableException(Exception ex) {
    return ApiResponse.fail(400, "请求体格式错误");
  }

  @ExceptionHandler(Exception.class)
  public ApiResponse<Void> handleDefault(Exception ex) {
    log.error("Unhandled exception", ex);
    return ApiResponse.fail(500, "服务器内部错误");
  }
}
