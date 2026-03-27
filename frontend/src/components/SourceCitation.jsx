import React, { useState } from 'react';

export const SourceCitation = ({ citations }) => {
    const [expandedIndex, setExpandedIndex] = useState(null);

    if (!citations || citations.length === 0) return null;

    return (
        <div className="citations-box">
            <div style={{width: '100%', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.25rem'}}>View Sources:</div>
            {citations.map((cit, idx) => (
                <div key={idx} style={{position: 'relative'}}>
                    <div 
                        className="citation-chip" 
                        onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
                    >
                        {cit.source} {cit.page && cit.page !== "None" ? `(p.${cit.page})` : ''} • {(cit.relevance_score * 100).toFixed(0)}%
                    </div>
                    {expandedIndex === idx && (
                        <div style={{
                            position: 'absolute', top: 'calc(100% + 5px)', left: 0, 
                            background: 'var(--bg-secondary)', padding: '10px', 
                            borderRadius: '8px', border: '1px solid var(--border-light)',
                            zIndex: 10, width: 'max-content', maxWidth: '300px',
                            boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)',
                            fontSize: '0.8rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap'
                        }}>
                            {cit.chunk_text}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};
