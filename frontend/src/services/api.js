const getDefaultApiBaseUrl = () => {
    if (typeof window === 'undefined') {
        return 'http://localhost:8000/api';
    }

    return `${window.location.protocol}//${window.location.hostname}:8000/api`;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || getDefaultApiBaseUrl();

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
        body: formData
    }).then(parseResponse);
};

export const getConversations = async () => {
    return fetch(`${API_BASE_URL}/conversations`).then(parseResponse);
};

export const getConversation = async (id) => {
    return fetch(`${API_BASE_URL}/conversations/${id}`).then(parseResponse);
};

export const deleteConversation = async (id) => {
    return fetch(`${API_BASE_URL}/conversations/${id}`, {
        method: 'DELETE'
    }).then(parseResponse);
};

export const getDocuments = async () => {
    return fetch(`${API_BASE_URL}/documents`).then(parseResponse);
};
