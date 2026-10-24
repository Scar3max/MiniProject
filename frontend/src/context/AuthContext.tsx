import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "../services/apiClient";
import type { paths, components } from "../types/api";

export type User = components["schemas"]["UserResponse"];

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isGuest: boolean;
  login: (credentials: paths["/api/auth/login"]["post"]["requestBody"]["content"]["application/json"]) => Promise<void>;
  register: (data: paths["/api/auth/register"]["post"]["requestBody"]["content"]["application/json"]) => Promise<void>;
  loginAsGuest: () => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const res = await api.me();
      setUser(res as unknown as User);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();

    const handleUnauthorized = () => {
      setUser(null);
    };

    window.addEventListener("interview_auth_unauthorized", handleUnauthorized);
    return () => window.removeEventListener("interview_auth_unauthorized", handleUnauthorized);
  }, [refreshUser]);

  const login = async (credentials: paths["/api/auth/login"]["post"]["requestBody"]["content"]["application/json"]) => {
    setIsLoading(true);
    try {
      const res = await api.login(credentials);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: paths["/api/auth/register"]["post"]["requestBody"]["content"]["application/json"]) => {
    setIsLoading(true);
    try {
      const res = await api.register(data);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const loginAsGuest = async () => {
    setIsLoading(true);
    try {
      const res = await api.guest();
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (e) {
      console.warn("Logout error:", e);
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        isGuest: !!user?.is_guest,
        login,
        register,
        loginAsGuest,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
