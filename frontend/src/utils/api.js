/**
 * Centralized API URL resolver for ProfitPilot AI.
 * Supports:
 * 1. Direct backend URL via VITE_API_BASE_URL (e.g. https://profitpilot.onrender.com)
 * 2. Relative URLs via Vercel rewrites or local Vite proxy (when VITE_API_BASE_URL is unset)
 */

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');

export function getApiUrl(endpoint = '') {
  if (!endpoint) return API_BASE_URL || '';
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${path}`;
}

export default getApiUrl;

