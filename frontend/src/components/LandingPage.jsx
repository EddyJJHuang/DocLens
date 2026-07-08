import React from 'react';

const capabilities = [
    {
        title: 'Document intelligence',
        eyebrow: 'RAG over files',
        body: 'Upload PDF, Markdown, or HTML. DocLens chunks, embeds, retrieves with FAISS and BM25, reranks results, then streams grounded answers with expandable citations.',
    },
    {
        title: 'Structured data answers',
        eyebrow: 'Text-to-SQL',
        body: 'Ask business questions in plain English. The assistant generates safe read-only SQL, validates it with sqlglot, executes it against a synthetic demand-planning database, and shows the query plus result table.',
    },
    {
        title: 'One routed workspace',
        eyebrow: 'Hybrid assistant',
        body: 'A lightweight router sends every question to documents, database, or both, so users do not need to choose tools before asking.',
    },
    {
        title: 'Ephemeral sessions',
        eyebrow: 'Bounded cache',
        body: 'Uploaded files and retrieval indexes are scoped to the current browser session, protected by upload limits, and cleaned up when the session ends or expires.',
    },
];

const pipeline = [
    'Ask',
    'Route',
    'Retrieve',
    'Query',
    'Verify',
    'Answer',
];

const metrics = [
    ['100%', 'starter Text-to-SQL execution accuracy'],
    ['SELECT-only', 'AST-validated SQL guard'],
    ['Session-scoped', 'bounded uploads and expiring cache'],
];

export const DocLensMark = ({ className = '' }) => (
    <span className={`brand-mark ${className}`} aria-hidden="true">
        <svg viewBox="0 0 48 48" role="img">
            <path d="M12 10.5h15.5L36 19v18.5H12z" />
            <path d="M27.5 10.5V19H36" />
            <path d="M17.5 27h13" />
            <path d="M17.5 32h9" />
            <circle cx="32.5" cy="31.5" r="6.5" />
            <path d="m37.5 36.5 4 4" />
        </svg>
    </span>
);

export const LandingPage = () => {
    return (
        <div className="landing-page">
            <header className="landing-nav">
                <a className="landing-brand" href="/" aria-label="DocLens home">
                    <DocLensMark />
                    <span>DocLens</span>
                </a>
                <nav className="landing-links" aria-label="Landing navigation">
                    <a href="#capabilities">Capabilities</a>
                    <a href="#architecture">Architecture</a>
                    <a href="#evaluation">Evaluation</a>
                </nav>
                <a className="nav-launch" href="/app">Launch app</a>
            </header>

            <main>
                <section className="landing-hero">
                    <div className="hero-copy">
                        <p className="hero-kicker">Hybrid RAG + Text-to-SQL assistant</p>
                        <h1>Ask your documents and business data in one AI workspace.</h1>
                        <p className="hero-subcopy">
                            DocLens combines file-grounded retrieval, safe SQL generation, source citations,
                            and streamed answers behind a single chat interface.
                        </p>
                        <div className="hero-actions">
                            <a className="primary-cta" href="/app">Launch DocLens <span aria-hidden="true">→</span></a>
                            <a className="secondary-cta" href="https://github.com/EddyJJHuang/DocLens">View repository</a>
                        </div>
                        <div className="hero-proof" aria-label="Project highlights">
                            {metrics.map(([value, label]) => (
                                <div key={label}>
                                    <strong>{value}</strong>
                                    <span>{label}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="hero-visual" aria-label="DocLens product preview">
                        <div className="signal-map" aria-hidden="true">
                            <svg className="signal-diagram" viewBox="0 0 560 200" role="img">
                                <defs>
                                    <filter id="nodeShadow" x="-30%" y="-45%" width="160%" height="190%">
                                        <feDropShadow dx="0" dy="14" stdDeviation="15" floodColor="#1f2d3d" floodOpacity="0.1" />
                                    </filter>
                                </defs>
                                <g className="signal-paths">
                                    <path className="wire wire-a" d="M134 60 C176 63 208 82 236 100" />
                                    <path className="wire wire-b" d="M134 140 C176 137 208 118 236 100" />
                                    <path className="wire wire-c" d="M344 100 H430" />
                                </g>
                                <g className="diagram-node muted" filter="url(#nodeShadow)">
                                    <rect x="36" y="40" width="98" height="40" rx="20" />
                                    <text x="85" y="61">Docs</text>
                                </g>
                                <g className="diagram-node data" filter="url(#nodeShadow)">
                                    <rect x="36" y="120" width="98" height="40" rx="20" />
                                    <text x="85" y="141">Data</text>
                                </g>
                                <g className="diagram-node router" filter="url(#nodeShadow)">
                                    <rect x="236" y="80" width="108" height="40" rx="20" />
                                    <text x="290" y="101">Router</text>
                                </g>
                                <g className="diagram-node answer" filter="url(#nodeShadow)">
                                    <rect x="430" y="80" width="108" height="40" rx="20" />
                                    <text x="484" y="101">Answer</text>
                                </g>
                            </svg>
                        </div>
                        <div className="preview-shell">
                            <div className="preview-topbar">
                                <span />
                                <span />
                                <span />
                                <strong>DocLens workspace</strong>
                            </div>
                            <div className="preview-body">
                                <div className="preview-question">
                                    Which products lead revenue, and how should I think about safety stock?
                                </div>
                                <div className="preview-answer">
                                    <div className="preview-route">Hybrid route</div>
                                    <p>
                                        Battery Pack, Battery Module, and Drive Unit lead total revenue. Safety stock
                                        is buffer inventory used to absorb demand and supply variability.
                                    </p>
                                    <div className="preview-sql">
                                        <code>SELECT p.name, SUM(s.revenue) AS revenue...</code>
                                    </div>
                                    <div className="preview-table">
                                        <span>Battery Pack</span><strong>$92.4M</strong>
                                        <span>Battery Module</span><strong>$78.1M</strong>
                                        <span>Drive Unit</span><strong>$45.6M</strong>
                                    </div>
                                    <div className="preview-citations">
                                        <span>glossary.md</span>
                                        <span>tables.md</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="capability-section" id="capabilities">
                    <div className="section-heading">
                        <p>Capabilities</p>
                        <h2>Built for questions that cross file boundaries and database tables.</h2>
                    </div>
                    <div className="capability-grid">
                        {capabilities.map((item) => (
                            <article className="capability-card" key={item.title}>
                                <span>{item.eyebrow}</span>
                                <h3>{item.title}</h3>
                                <p>{item.body}</p>
                            </article>
                        ))}
                    </div>
                </section>

                <section className="architecture-section" id="architecture">
                    <div className="section-heading">
                        <p>Architecture</p>
                        <h2>One question travels through a transparent evidence pipeline.</h2>
                    </div>
                    <div className="pipeline" aria-label="DocLens request pipeline">
                        {pipeline.map((step, index) => (
                            <div className="pipeline-step" style={{ '--delay': `${index * 90}ms` }} key={step}>
                                <span>{String(index + 1).padStart(2, '0')}</span>
                                <strong>{step}</strong>
                            </div>
                        ))}
                    </div>
                    <div className="architecture-notes">
                        <div>
                            <h3>Document path</h3>
                            <p>FAISS dense retrieval and BM25 sparse retrieval are fused, reranked, and returned with citations.</p>
                        </div>
                        <div>
                            <h3>Database path</h3>
                            <p>Schema context and dynamic few-shot examples guide SQL generation before read-only execution.</p>
                        </div>
                        <div>
                            <h3>Hybrid path</h3>
                            <p>DocLens can combine retrieved passages and SQL rows in a single streamed answer.</p>
                        </div>
                    </div>
                </section>

                <section className="evaluation-section" id="evaluation">
                    <div className="evaluation-copy">
                        <p className="hero-kicker">Measured, not hand-waved</p>
                        <h2>Includes a reproducible Text-to-SQL evaluation harness.</h2>
                        <p>
                            The project ships with a starter benchmark over a synthetic demand-planning database,
                            result-set matching, model cost estimates, and a generated leaderboard.
                        </p>
                    </div>
                    <div className="leaderboard-card">
                        <div className="leaderboard-row heading">
                            <span>Model</span><span>Exec accuracy</span><span>Latency</span>
                        </div>
                        <div className="leaderboard-row">
                            <span>gpt-4o-mini</span><strong>100%</strong><span>1.71s</span>
                        </div>
                        <div className="leaderboard-row">
                            <span>gpt-4o</span><strong>100%</strong><span>1.08s</span>
                        </div>
                        <div className="leaderboard-row">
                            <span>gemini-2.5-flash</span><strong>83.3%</strong><span>0.84s</span>
                        </div>
                    </div>
                </section>

                <section className="final-cta">
                    <h2>Explore the working assistant.</h2>
                    <p>Open the app, upload documents for the current session, and ask across both files and the synthetic database.</p>
                    <a className="primary-cta" href="/app">Launch DocLens <span aria-hidden="true">→</span></a>
                </section>
            </main>
        </div>
    );
};
