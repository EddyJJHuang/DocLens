import { API_BASE_URL } from '../config';

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

export const sqlQuery = async (q) => {
    return fetch(`${API_BASE_URL}/sql-query?q=${encodeURIComponent(q)}`).then(parseResponse);
};
