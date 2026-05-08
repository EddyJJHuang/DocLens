import { useState, useCallback } from 'react';

const getDefaultApiBaseUrl = () => {
    if (typeof window === 'undefined') {
        return 'http://localhost:8000/api';
    }

    return `${window.location.protocol}//${window.location.hostname}:8000/api`;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || getDefaultApiBaseUrl();

export const useSSE = () => {
    const [isStreaming, setIsStreaming] = useState(false);
    
    const streamQuery = useCallback(async (query, conversationId, onToken, onCitations, onError) => {
        setIsStreaming(true);
        try {
            const url = `${API_BASE_URL}/query?q=${encodeURIComponent(query)}&conversation_id=${encodeURIComponent(conversationId)}`;
            const response = await fetch(url, { method: 'GET' });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Server error: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                
                // Keep the last incomplete chunk in buffer if the packet was fragmented
                buffer = lines.pop() || "";
                
                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const dataStr = line.substring(6);
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.type === "token") {
                                onToken(data.content);
                            } else if (data.type === "citations") {
                                onCitations(data.citations);
                            }
                        } catch (e) {
                            console.error("Error parsing SSE packet:", e, dataStr);
                        }
                    }
                }
            }
        } catch (error) {
            onError(error.message);
        } finally {
            setIsStreaming(false);
        }
    }, []);

    return { isStreaming, streamQuery };
};
