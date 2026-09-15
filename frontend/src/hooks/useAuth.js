import { useState } from "react";

import {
  registerRequest,
  loginRequest,
} from "../services/authService";

export function useAuth() {
  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem("quizblast_user");
    return storedUser ? JSON.parse(storedUser) : null;
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

  const clearAuth = () => {
    localStorage.removeItem("quizblast_user");
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
    register,
    login,
    clearAuth,
  };
}
