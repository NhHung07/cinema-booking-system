import api from "./axios";
import type { LoginPayload, RegisterPayload, TokenResponse, User } from "../types/auth";

export async function register(payload: RegisterPayload): Promise<User> {
  const response = await api.post<User>("/auth/register", payload);
  return response.data;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/auth/login", payload);
  return response.data;
}
