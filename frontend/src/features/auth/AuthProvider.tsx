import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getMe, login as apiLogin, register as apiRegister } from "@/api/auth";
import { getAuthToken, clearAuthToken, registerUnauthorizedHandler, ApiError } from "@/api/http";
import type { UserResponse, UserLoginRequest, UserRegisterRequest } from "@/api/types";
import { useToast } from "@/components/ui/Toast";
import { useQueryClient } from "@tanstack/react-query";

export type AuthStatus = "loading" | "authenticated" | "guest";

export interface AuthContextType {
  user: UserResponse | null;
  status: AuthStatus;
  login: (payload: UserLoginRequest) => Promise<UserResponse>;
  register: (payload: UserRegisterRequest) => Promise<UserResponse>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const toast = useToast();
  const queryClient = useQueryClient();

  const logout = useCallback(() => {
    clearAuthToken();
    setUser(null);
    setStatus("guest");
    queryClient.clear();
  }, [queryClient]);

  // Initial session verification
  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setStatus("guest");
      return;
    }

    let isMounted = true;
    getMe()
      .then((userData) => {
        if (isMounted) {
          setUser(userData);
          setStatus("authenticated");
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          if (err instanceof ApiError && err.status === 401) {
            clearAuthToken();
            setUser(null);
            setStatus("guest");
          } else {
            // Keep token intact across transient network drops / 5xx server glitches
            setStatus("guest");
          }
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Connect 401 unauthorized handler without circular imports
  useEffect(() => {
    registerUnauthorizedHandler(() => {
      logout();
      toast.error("Your session expired. Please sign in again.");
    });

    const handleSessionExpiredEvent = () => {
      logout();
      toast.error("Your session expired. Please sign in again.");
    };

    window.addEventListener("session-expired", handleSessionExpiredEvent);

    return () => {
      registerUnauthorizedHandler(null);
      window.removeEventListener("session-expired", handleSessionExpiredEvent);
    };
  }, [logout, toast]);

  const login = useCallback(
    async (payload: UserLoginRequest): Promise<UserResponse> => {
      await apiLogin(payload);
      const userData = await getMe();
      setUser(userData);
      setStatus("authenticated");
      return userData;
    },
    []
  );

  const register = useCallback(
    async (payload: UserRegisterRequest): Promise<UserResponse> => {
      const res = await apiRegister(payload);
      // If token not present on register response, login explicitly
      if (!res.access_token) {
        await apiLogin({ email: payload.email, password: payload.password });
      }
      const userData = await getMe();
      setUser(userData);
      setStatus("authenticated");
      return userData;
    },
    []
  );

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export default AuthProvider;
