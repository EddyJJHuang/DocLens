import { useState, useCallback } from 'react';

export const useSSE = () => {
    const [isStreaming, setIsStreaming] = useState(false);
    
    const streamQuery = useCallback(async (query, conversationId, onToken, onCitations, onError) => {
        setIsStreaming(true);
        try {
            const url = `http://localhost:8000/api/query?q=${encodeURIComponent(query)}&conversation_id=${encodeURIComponent(conversationId)}`;
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
