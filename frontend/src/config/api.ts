/**
 * API Configuration
 * Backend URL configuration for connecting to the VeriFact API
 */

// Get backend URL from environment variable or use default
const getBackendUrl = (): string => {
  // In Vite, environment variables are prefixed with VITE_
  const envUrl = import.meta.env.VITE_API_URL;
  
  if (envUrl) {
    return envUrl;
  }
  
  // Default to localhost:8000 for development
  return 'http://localhost:8000';
};

export const API_CONFIG = {
  // Base URL for the backend API
  baseUrl: getBackendUrl(),
  
  // WebSocket endpoint path (will be appended to baseUrl)
  wsPath: '/api/v1/ws/verify',
  
  // Get full WebSocket URL for a user
  getWebSocketUrl: (userId: string): string => {
    const base = API_CONFIG.baseUrl.replace(/^http/, 'ws');
    return `${base}${API_CONFIG.wsPath}/${userId}`;
  },
  
  // Health check endpoint
  healthEndpoint: '/health',
};

