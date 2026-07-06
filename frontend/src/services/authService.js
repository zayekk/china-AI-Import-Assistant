/**
 * Service API : authentification.
 */
import apiClient from "./apiClient";

export async function register(email, password, fullName) {
  const { data } = await apiClient.post("/auth/register", {
    email,
    password,
    full_name: fullName,
  });
  return data;
}

export async function login(email, password) {
  const { data } = await apiClient.post("/auth/login", { email, password });
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export async function getCurrentUser() {
  const { data } = await apiClient.get("/auth/me");
  return data;
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem("access_token"));
}
