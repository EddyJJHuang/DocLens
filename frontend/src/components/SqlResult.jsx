import React, { useState } from 'react';

const MAX_TABLE_ROWS = 20;

const formatCell = (value) => {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'number') {
        return Number.isInteger(value)
            ? value.toLocaleString()
            : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
    return String(value);
};

/**
 * Renders a Text-to-SQL result: the generated (read-only) SQL and a preview
 * table of the returned rows. Mirrors how RAG answers surface their citations.
 */
export const SqlResult = ({ sql, columns = [], rows = [], rowCount = 0, repaired = false }) => {
    const [showSql, setShowSql] = useState(false);
    if (!sql) return null;

    const previewRows = rows.slice(0, MAX_TABLE_ROWS);

    return (
        <div className="sql-result">
            <div className="sql-toolbar">
                <button className="sql-toggle" onClick={() => setShowSql((v) => !v)}>
                    {showSql ? 'Hide SQL' : 'View generated SQL'}
                </button>
                {repaired && <span className="sql-badge" title="The query was auto-repaired once">self-repaired</span>}
                <span className="sql-count">{rowCount} row{rowCount === 1 ? '' : 's'}</span>
            </div>

            {showSql && <pre className="sql-code">{sql}</pre>}

            {previewRows.length > 0 && (
                <div className="sql-table-wrap">
                    <table className="sql-table">
                        <thead>
                            <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
                        </thead>
                        <tbody>
                            {previewRows.map((row, i) => (
                                <tr key={i}>
                                    {columns.map((c) => <td key={c}>{formatCell(row[c])}</td>)}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {rowCount > previewRows.length && (
                        <div className="sql-more">Showing {previewRows.length} of {rowCount} rows</div>
                    )}
                </div>
            )}
        </div>
    );
};
