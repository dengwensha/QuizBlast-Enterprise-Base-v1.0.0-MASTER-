const HOST = window.location.hostname;

export const API = `http://${HOST}:8001`;
export const WS = `ws://${HOST}:8001`;
export const APP_URL = `http://${HOST}:5173`;

export const authHeaders = (user) => ({
  Authorization: `Bearer ${user?.token}`,
});

export const jsonAuthHeaders = (user) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${user?.token}`,
});