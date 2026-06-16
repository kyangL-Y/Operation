import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080/api";

const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 8000
});

http.interceptors.request.use((config) => {
  const url = String(config.url || "");
  const isPublicAuth = url.includes("/auth/login") || url.includes("/auth/register");
  const token = localStorage.getItem("auth_token");
  if (!isPublicAuth && token) {
    config.headers["X-Auth-Token"] = token;
  }
  return config;
});

export default http;
