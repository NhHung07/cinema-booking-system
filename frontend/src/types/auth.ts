export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  role: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  created_at: string | null;
}
