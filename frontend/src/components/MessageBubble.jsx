import React from 'react';
import { SourceCitation } from './SourceCitation';

export const MessageBubble = ({ role, content, citations }) => {
    return (
        <div className={`message-row ${role}`}>
            <div className={`bubble ${role}`}>
                <div className="message-content">{content}</div>
                {role === 'assistant' && citations && citations.length > 0 && (
                    <SourceCitation citations={citations} />
                )}
            </div>
        </div>
    );
};
