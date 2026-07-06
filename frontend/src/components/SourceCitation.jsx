import React, { useState } from 'react';

export const SourceCitation = ({ citations }) => {
    const [expandedIndex, setExpandedIndex] = useState(null);

    if (!citations || citations.length === 0) return null;

    return (
        <div className="citations-box">
            <div className="citations-label">Sources</div>
            {citations.map((cit, idx) => {
                const pct = Math.round((cit.relevance_score ?? 0) * 100);
                const hasScore = (cit.relevance_score ?? 0) > 0;
                const page = cit.page && cit.page !== 'None' && cit.page !== '' ? ` · p.${cit.page}` : '';
                return (
                    <div key={idx} style={{ position: 'relative' }}>
                        <div
                            className="citation-chip"
                            onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
                            title={hasScore ? `Relevance to your question: ${pct}%` : undefined}
                        >
                            <span className="citation-name">📄 {cit.source}{page}</span>
                            {hasScore && (
                                <span className="relevance-meter" aria-label={`relevance ${pct}%`}>
                                    <span className="relevance-fill" style={{ width: `${pct}%` }} />
                                </span>
                            )}
                        </div>
                        {expandedIndex === idx && (
                            <div className="citation-popover">{cit.chunk_text}</div>
                        )}
                    </div>
                );
            })}
        </div>
    );
};
