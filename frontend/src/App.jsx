import React, { useState } from 'react';
import { MessageBubble } from './components/MessageBubble';
import { DocumentUpload } from './components/DocumentUpload';
import { useSSE } from './hooks/useSSE';
import './styles/global.css';

function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [conversationId] = useState(`conv_${Date.now()}`); // Simple tracking
    const { isStreaming, streamQuery } = useSSE();
    const [errorBanner, setErrorBanner] = useState("");

    const handleSend = async () => {
        if (!input.trim() || isStreaming) return;
        
        const q = input;
        setInput("");
        setErrorBanner("");
        
        // Push user query implicitly
        setMessages(prev => [
            ...prev, 
            { role: 'user', content: q },
            { role: 'assistant', content: '', citations: [] }
        ]);

        await streamQuery(
            q, 
            conversationId,
            (token) => {
                setMessages(prev => {
                    const newMwges = [...prev];
                    const target = newMwges.length - 1;
                    newMwges[target].content += token;
                    return newMwges;
                });
            },
            (citations) => {
                setMessages(prev => {
                    const newMwges = [...prev];
                    const target = newMwges.length - 1;
                    newMwges[target].citations = citations;
                    return newMwges;
                });
            },
            (errStr) => {
                setErrorBanner(errStr);
                // Cutout failure payload safely
                setMessages(prev => prev.slice(0, -1)); 
            }
        );
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
                <h2>DocLens</h2>
                
                <div style={{flex: 1}}>
                    <div className="conv-item active">Current Session</div>
                </div>
                
                <DocumentUpload />
            </aside>
            
            <main className="chat-area">
                {errorBanner && (
                    <div style={{background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', padding: '10px 20px', textAlign: 'center'}}>
                        {errorBanner}
                    </div>
                )}
                
                <div className="messages-container">
                    {messages.length === 0 ? (
                        <div style={{textAlign: 'center', marginTop: '20vh', color: 'var(--text-secondary)'}}>
                            <h1 style={{fontSize: '2.5rem', color: 'var(--text-primary)', marginBottom: '1rem'}}>Ask DocLens</h1>
                            <p>Upload a document on the left sidebar to initialize the AI's context capabilities.</p>
                        </div>
                    ) : (
                        messages.map((msg, i) => (
                            <MessageBubble key={i} role={msg.role} content={msg.content} citations={msg.citations} />
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

export default App;
