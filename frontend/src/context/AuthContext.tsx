import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { TOKEN_STORAGE_KEY } from "../api/axios";

export const USER_EMAIL_STORAGE_KEY = "cinema_user_email";

interface AuthContextValue {
  token: string | null;
  userEmail: string | null;
  isAuthenticated: boolean;
  login: (accessToken: string, email?: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => window.localStorage.getItem(TOKEN_STORAGE_KEY));
  const [userEmail, setUserEmail] = useState<string | null>(() => window.localStorage.getItem(USER_EMAIL_STORAGE_KEY));

  const login = useCallback((accessToken: string, email?: string) => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    setToken(accessToken);
    if (email) {
      window.localStorage.setItem(USER_EMAIL_STORAGE_KEY, email);
      setUserEmail(email);
    }
  }, []);

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(USER_EMAIL_STORAGE_KEY);
    setToken(null);
    setUserEmail(null);
  }, []);

  const value = useMemo(
    () => ({
      token,
      userEmail,
      isAuthenticated: token !== null,
      login,
      logout,
    }),
    [login, logout, token, userEmail],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth phải được dùng bên trong AuthProvider.");
  }
  return context;
}
