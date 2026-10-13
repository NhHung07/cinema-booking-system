import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { TOKEN_STORAGE_KEY } from "../api/axios";
import { getMe } from "../api/authApi";

export const USER_EMAIL_STORAGE_KEY = "cinema_user_email";
export const USER_ROLE_STORAGE_KEY = "cinema_user_role";
export const USER_NAME_STORAGE_KEY = "cinema_user_name";

interface AuthContextValue {
  token: string | null;
  userEmail: string | null;
  userName: string | null;
  role: string | null;
  isAdmin: boolean;
  isAuthenticated: boolean;
  login: (accessToken: string, email?: string, role?: string, name?: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => window.localStorage.getItem(TOKEN_STORAGE_KEY));
  const [userEmail, setUserEmail] = useState<string | null>(() => window.localStorage.getItem(USER_EMAIL_STORAGE_KEY));
  const [userName, setUserName] = useState<string | null>(() => window.localStorage.getItem(USER_NAME_STORAGE_KEY));
  const [role, setRole] = useState<string | null>(() => window.localStorage.getItem(USER_ROLE_STORAGE_KEY));

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(USER_EMAIL_STORAGE_KEY);
    window.localStorage.removeItem(USER_ROLE_STORAGE_KEY);
    window.localStorage.removeItem(USER_NAME_STORAGE_KEY);
    setToken(null);
    setUserEmail(null);
    setUserName(null);
    setRole(null);
  }, []);

  const login = useCallback((accessToken: string, email?: string, userRole?: string, name?: string) => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    setToken(accessToken);
    if (email) {
      window.localStorage.setItem(USER_EMAIL_STORAGE_KEY, email);
      setUserEmail(email);
    }
    const resolvedRole = userRole || "user";
    window.localStorage.setItem(USER_ROLE_STORAGE_KEY, resolvedRole);
    setRole(resolvedRole);

    if (name) {
      window.localStorage.setItem(USER_NAME_STORAGE_KEY, name);
      setUserName(name);
    }
  }, []);

  useEffect(() => {
    if (token) {
      getMe()
        .then((user) => {
          if (user.role) {
            setRole(user.role);
            window.localStorage.setItem(USER_ROLE_STORAGE_KEY, user.role);
          }
          if (user.email) {
            setUserEmail(user.email);
            window.localStorage.setItem(USER_EMAIL_STORAGE_KEY, user.email);
          }
          if (user.full_name) {
            setUserName(user.full_name);
            window.localStorage.setItem(USER_NAME_STORAGE_KEY, user.full_name);
          }
        })
        .catch(() => {
          // Token expired or invalid -> log out to clear corrupted auth state
          logout();
        });
    }
  }, [token, logout]);

  const value = useMemo(
    () => ({
      token,
      userEmail,
      userName,
      role,
      isAdmin: role === "admin",
      isAuthenticated: token !== null,
      login,
      logout,
    }),
    [login, logout, token, userEmail, userName, role],
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
