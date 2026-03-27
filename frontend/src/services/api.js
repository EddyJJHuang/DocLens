import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api'
});

export const uploadDocument = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};

export const getConversations = async () => {
    return api.get('/conversations');
};

export const deleteConversation = async (id) => {
    return api.delete(`/conversations/${id}`);
};
