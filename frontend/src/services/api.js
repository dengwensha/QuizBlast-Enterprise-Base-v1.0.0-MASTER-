const ORIGIN = window.location.origin;

export const API = `${ORIGIN}/api`;
export const WS = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;
export const APP_URL = ORIGIN;

export const authHeaders = (user) => ({
  Authorization: `Bearer ${user?.token}`,
});

export const jsonAuthHeaders = (user) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${user?.token}`,
});