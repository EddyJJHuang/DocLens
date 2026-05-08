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
                        <div className="citation-popover">
                            {cit.chunk_text}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};
