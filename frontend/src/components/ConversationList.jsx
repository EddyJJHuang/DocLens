import React from 'react';

export const ConversationList = ({ conversations, activeId, onSelect, onNewConversation }) => {
    const entries = Object.entries(conversations || {}).sort(([a], [b]) => b.localeCompare(a));

    return (
        <div className="conversation-panel">
            <button className="new-conversation-btn" onClick={onNewConversation}>
                New chat
            </button>
            <div className="conversation-list" aria-label="Conversation history">
                {entries.length === 0 ? (
                    <div className="empty-note">No saved chats yet</div>
                ) : (
                    entries.map(([id, messages]) => {
                        const firstUserMessage = messages.find((message) => message.role === 'user');
                        const title = firstUserMessage?.content || 'Untitled conversation';
                        return (
                            <button
                                key={id}
                                className={`conv-item ${id === activeId ? 'active' : ''}`}
                                onClick={() => onSelect(id)}
                                title={title}
                            >
                                {title}
                            </button>
                        );
                    })
                )}
            </div>
        </div>
    );
};
