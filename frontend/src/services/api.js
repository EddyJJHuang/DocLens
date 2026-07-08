import { API_BASE_URL } from '../config';

const SESSION_KEY = 'doclens_session_id';
const SESSION_HEADER = 'X-DocLens-Session';

export const getSessionId = () => {
    if (typeof window === 'undefined') return 'server-session';
    let sessionId = window.sessionStorage.getItem(SESSION_KEY);
    if (!sessionId) {
        sessionId = window.crypto?.randomUUID?.() || `session_${Date.now()}_${Math.random().toString(36).slice(2)}`;
        window.sessionStorage.setItem(SESSION_KEY, sessionId);
    }
    return sessionId;
};

const sessionHeaders = () => ({
    [SESSION_HEADER]: getSessionId(),
});

const parseResponse = async (response) => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || `Server error: ${response.status}`);
    }
    return { data };
};

export const uploadDocument = async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    onUploadProgress?.({ loaded: file.size, total: file.size });

    return fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        headers: sessionHeaders(),
        body: formData
    }).then(parseResponse);
};

export const getConversations = async () => {
    return fetch(`${API_BASE_URL}/conversations`, {
        headers: sessionHeaders()
    }).then(parseResponse);
};

export const getConversation = async (id) => {
    return fetch(`${API_BASE_URL}/conversations/${id}`, {
        headers: sessionHeaders()
    }).then(parseResponse);
};

export const deleteConversation = async (id) => {
    return fetch(`${API_BASE_URL}/conversations/${id}`, {
        method: 'DELETE',
        headers: sessionHeaders()
    }).then(parseResponse);
};

export const getDocuments = async () => {
    return fetch(`${API_BASE_URL}/documents`, {
        headers: sessionHeaders()
    }).then(parseResponse);
};

export const sqlQuery = async (q) => {
    return fetch(`${API_BASE_URL}/sql-query?q=${encodeURIComponent(q)}`, {
        headers: sessionHeaders()
    }).then(parseResponse);
};

export const endSession = () => {
    const sessionId = getSessionId();
    return fetch(`${API_BASE_URL}/session/end`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...sessionHeaders(),
        },
        body: JSON.stringify({ session_id: sessionId }),
        keepalive: true,
    });
};
