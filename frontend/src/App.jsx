import React, { useEffect, useMemo, useState } from 'react';
import { MessageBubble } from './components/MessageBubble';
import { DocumentUpload } from './components/DocumentUpload';
import { ConversationList } from './components/ConversationList';
import { DocLensMark, LandingPage } from './components/LandingPage';
import { useSSE } from './hooks/useSSE';
import { endSession, getConversation, getConversations, getDocuments } from './services/api';
import './styles/global.css';

const createConversationId = () => `conv_${Date.now()}`;

const samplePrompts = [
    'What is safety stock?',
    'Which 3 products have the highest revenue?',
    'Compare demand volatility with document guidance.',
];

function WorkspaceApp() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [conversationId, setConversationId] = useState(createConversationId());
    const [conversations, setConversations] = useState({});
    const [documents, setDocuments] = useState([]);
    const { isStreaming, streamQuery } = useSSE();
    const [errorBanner, setErrorBanner] = useState("");

    const loadedDocumentCount = useMemo(
        () => documents.filter((doc) => doc.status === 'completed').length,
        [documents]
    );

    const refreshSidebar = async () => {
        const [conversationResponse, documentResponse] = await Promise.all([
            getConversations(),
            getDocuments()
        ]);
        setConversations(conversationResponse.data);
        setDocuments(documentResponse.data);
    };

    useEffect(() => {
        refreshSidebar().catch((error) => setErrorBanner(error.message));
    }, []);

    useEffect(() => {
        const cleanupSession = () => {
            endSession().catch(() => {});
        };
        window.addEventListener('pagehide', cleanupSession);
        return () => {
            window.removeEventListener('pagehide', cleanupSession);
        };
    }, []);

    const handleNewConversation = () => {
        setConversationId(createConversationId());
        setMessages([]);
        setErrorBanner("");
    };

    const handleSelectConversation = async (id) => {
        setConversationId(id);
        setErrorBanner("");
        try {
            const response = await getConversation(id);
            setMessages(response.data);
        } catch (error) {
            setErrorBanner(error.message);
        }
    };

    const handleSend = async () => {
        if (!input.trim() || isStreaming) return;
        
        const q = input;
        setInput("");
        setErrorBanner("");
        
        // Push the user query + an empty assistant placeholder.
        setMessages(prev => [
            ...prev,
            { role: 'user', content: q },
            { role: 'assistant', content: '', citations: [], route: null, sql: null }
        ]);

        // Immutable update of the last (assistant) message. Mutating in place
        // doubled tokens under React StrictMode.
        const updateLast = (fn) =>
            setMessages(prev => prev.map((msg, i) => (i === prev.length - 1 ? fn(msg) : msg)));

        await streamQuery(q, conversationId, {
            onRoute: (route) => updateLast(m => ({ ...m, route })),
            onSqlResult: (payload) => updateLast(m => ({ ...m, sql: payload })),
            onToken: (token) => updateLast(m => ({ ...m, content: m.content + token })),
            onCitations: (citations) => updateLast(m => ({ ...m, citations })),
            onError: (errStr) => {
                setErrorBanner(errStr);
                setMessages(prev => prev.slice(0, -1)); // drop the failed assistant bubble
            },
        });
        refreshSidebar().catch(() => {});
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="app-container">
            <aside className="sidebar">
                <div className="brand-block">
                    <a className="app-brand-link" href="/" aria-label="DocLens overview">
                        <DocLensMark className="app-brand-mark" />
                        <span>
                            <strong>DocLens</strong>
                            <small>{loadedDocumentCount} ready documents</small>
                        </span>
                    </a>
                </div>
                
                <ConversationList
                    conversations={conversations}
                    activeId={conversationId}
                    onSelect={handleSelectConversation}
                    onNewConversation={handleNewConversation}
                />
                
                <div className="document-list">
                    {documents.slice(-4).map((doc) => (
                        <div className="document-row" key={doc.id}>
                            <span>{doc.filename}</span>
                            <small>{doc.status}</small>
                        </div>
                    ))}
                </div>

                <DocumentUpload onUploadSuccess={() => setTimeout(() => refreshSidebar().catch(() => {}), 800)} />
            </aside>
            
            <main className="chat-area">
                {errorBanner && (
                    <div className="error-banner">
                        {errorBanner}
                    </div>
                )}
                
                <div className="messages-container">
                    {messages.length === 0 ? (
                        <div className="empty-workspace">
                            <DocLensMark className="workspace-mark" />
                            <p className="workspace-kicker">Evidence workspace</p>
                            <h1>Ask DocLens</h1>
                            <p className="workspace-subcopy">
                                Ask about uploaded documents, query the demand-planning database,
                                or let DocLens combine both evidence paths in one answer.
                            </p>
                            <div className="workspace-stats" aria-label="Workspace status">
                                <span><strong>{loadedDocumentCount}</strong> ready docs</span>
                                <span><strong>SQL</strong> guarded</span>
                                <span><strong>RAG</strong> cited</span>
                            </div>
                            <div className="prompt-grid">
                                {samplePrompts.map((prompt) => (
                                    <button
                                        className="prompt-card"
                                        key={prompt}
                                        onClick={() => setInput(prompt)}
                                        type="button"
                                    >
                                        {prompt}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        messages.map((msg, i) => (
                            <MessageBubble
                                key={i}
                                role={msg.role}
                                content={msg.content}
                                citations={msg.citations}
                                route={msg.route}
                                sql={msg.sql}
                            />
                        ))
                    )}
                </div>
                
                <div className="input-container">
                    <div className="input-box">
                        <input 
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask a question..."
                            disabled={isStreaming}
                        />
                        <button className="send-btn" onClick={handleSend} disabled={isStreaming || !input.trim()}>
                            {isStreaming ? 'Thinking' : 'Send'}
                        </button>
                    </div>
                </div>
            </main>
        </div>
    );
}

function App() {
    const path = typeof window !== 'undefined' ? window.location.pathname : '/';
    if (path === '/' || path === '') {
        return <LandingPage />;
    }
    return <WorkspaceApp />;
}

export default App;
