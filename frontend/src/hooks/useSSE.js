import { useState, useCallback } from 'react';
import { API_BASE_URL } from '../config';

/**
 * Streams a unified query response. `handlers` may include:
 *   onRoute(route), onSqlResult(payload), onToken(text), onCitations(list), onError(message)
 */
export const useSSE = () => {
    const [isStreaming, setIsStreaming] = useState(false);

    const streamQuery = useCallback(async (query, conversationId, handlers = {}) => {
        const { onRoute, onSqlResult, onToken, onCitations, onError } = handlers;
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
                // Keep the last (possibly incomplete) chunk buffered.
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    let data;
                    try {
                        data = JSON.parse(line.substring(6));
                    } catch {
                        continue; // ignore malformed/partial frames
                    }

                    if (data.type === "route") onRoute?.(data.route);
                    else if (data.type === "sql_result") onSqlResult?.(data);
                    else if (data.type === "token") onToken?.(data.content);
                    else if (data.type === "citations") onCitations?.(data.citations);
                    else if (data.type === "error") {
                        await reader.cancel().catch(() => {});
                        onError?.(data.message || "The server reported an error.");
                        return;
                    }
                }
            }
        } catch (error) {
            onError?.(error.message);
        } finally {
            setIsStreaming(false);
        }
    }, []);

    return { isStreaming, streamQuery };
};
