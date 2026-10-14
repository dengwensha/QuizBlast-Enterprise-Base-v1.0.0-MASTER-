const ORIGIN = window.location.origin;

export const API = `${ORIGIN}/api`;
export const WS = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;
// QR invitations must use an address reachable by players on other devices.
// Configure VITE_PUBLIC_APP_URL at build time for LAN testing or production.
// The current origin remains the default when no public URL is configured.
const configuredAppUrl = import.meta.env.VITE_PUBLIC_APP_URL?.trim();
export const APP_URL = configuredAppUrl
  ? new URL(configuredAppUrl, ORIGIN).origin
  : ORIGIN;

export const authHeaders = (user) => ({
  Authorization: `Bearer ${user?.token}`,
});

export const jsonAuthHeaders = (user) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${user?.token}`,
});