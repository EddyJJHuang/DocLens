import React from 'react';
import { SourceCitation } from './SourceCitation';
import { SqlResult } from './SqlResult';

const ROUTE_LABELS = {
    structured: '🗄️ Database',
    unstructured: '📄 Documents',
    hybrid: '🔀 Hybrid',
};

export const MessageBubble = ({ role, content, citations, route, sql }) => {
    const isAssistant = role === 'assistant';
    return (
        <div className={`message-row ${role}`}>
            <div className={`bubble ${role}`}>
                {isAssistant && route && (
                    <div className="route-badge">{ROUTE_LABELS[route] || route}</div>
                )}
                <div className="message-content">{content}</div>
                {isAssistant && sql && (
                    <SqlResult
                        sql={sql.sql}
                        columns={sql.columns}
                        rows={sql.rows}
                        rowCount={sql.row_count}
                        repaired={sql.repaired}
                    />
                )}
                {isAssistant && citations && citations.length > 0 && (
                    <SourceCitation citations={citations} />
                )}
            </div>
        </div>
    );
};
