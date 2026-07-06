// Single source of truth for the backend API base URL.
// Override with VITE_API_BASE_URL at build time (e.g. "/api" behind a reverse proxy).
const getDefaultApiBaseUrl = () => {
    if (typeof window === 'undefined') {
        return 'http://localhost:8000/api';
    }

    return `${window.location.protocol}//${window.location.hostname}:8000/api`;
};

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || getDefaultApiBaseUrl();
