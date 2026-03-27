import React from 'react';
import { SourceCitation } from './SourceCitation';
import ReactMarkdown from 'react-markdown';

export const MessageBubble = ({ role, content, citations }) => {
    return (
        <div className={`message-row ${role}`}>
            <div className={`bubble ${role}`}>
                {role === 'assistant' ? (
                    <ReactMarkdown>{content}</ReactMarkdown>
                ) : (
                    content
                )}
                {role === 'assistant' && citations && citations.length > 0 && (
                    <SourceCitation citations={citations} />
                )}
            </div>
        </div>
    );
};
