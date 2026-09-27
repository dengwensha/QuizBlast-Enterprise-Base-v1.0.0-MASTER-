import { useState } from "react";

import {
  registerRequest,
  loginRequest,
} from "../services/authService";

function tokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp !== "number" || payload.exp * 1000 <= Date.now();
  } catch {
    return true;
  }
}

export function useAuth() {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem("quizblast_user");
    try {
      const parsed = storedUser ? JSON.parse(storedUser) : null;
      return parsed?.token && !tokenExpired(parsed.token) ? parsed : null;
    } catch { return null; }
  });
  const [authMode, setAuthMode] = useState("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");

  const register = async () => {
    try {
      const data = await registerRequest(authEmail, authPassword);

      if (data.error) {
        return alert(data.error);
      }

      alert("Kayıt başarılı.");
      setAuthMode("login");
    } catch (err) {
      console.error(err);
      alert(
        "Backend bağlantısı kurulamadı. Mobilde bilgisayar IP adresiyle açtığından ve CORS ayarından emin ol."
      );
    }
  };

  const login = async () => {
    try {
      const data = await loginRequest(authEmail, authPassword);

      if (data.error) {
        return alert("Giriş başarısız");
      }

      const savedSession = JSON.parse(sessionStorage.getItem("quizblast_active_session") || localStorage.getItem("quizblast_active_session") || "null");
      const previousUser = JSON.parse(localStorage.getItem("quizblast_user") || "null");
      if (savedSession?.who === "HOST" && previousUser?.email && previousUser.email !== data.email) {
        return alert("Oyuna dönmek için aynı host hesabıyla giriş yap.");
      }

      const authenticatedUser = {
        email: data.email,
        token: data.access_token,
      };

      localStorage.setItem(
        "quizblast_user",
        JSON.stringify(authenticatedUser)
      );
      setUser(authenticatedUser);
    } catch (err) {
      console.error(err);
      alert(
        "Backend bağlantısı kurulamadı. Mobilde bilgisayar IP adresiyle açtığından ve CORS ayarından emin ol."
      );
    }
  };

  const clearAuth = (preservePreviousUser = false) => {
    if (!preservePreviousUser) localStorage.removeItem("quizblast_user");
    setUser(null);
  };

  return {
    user,
    authMode,
    setAuthMode,
    authEmail,
    setAuthEmail,
    authPassword,
    setAuthPassword,
    tokenExpired,
    register,
    login,
    clearAuth,
  };
}
