import React, { useState } from 'react';
import { searchAPI } from '../utils/api';

function ArticleCard({ article }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div style={{
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 12, padding: 16, marginBottom: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0', marginBottom: 4 }}>
            {article.title}
          </div>
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>
            {article.journal && <span>{article.journal}</span>}
            {article.pub_date && <span> · {article.pub_date}</span>}
            {article.pmid && (
              <span> · <a
                href={`https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/`}
                target="_blank" rel="noreferrer"
                style={{ color: '#6366f1' }}
              >PMID {article.pmid}</a></span>
            )}
          </div>
        </div>
        <div style={{
          background: 'rgba(99,102,241,0.2)',
          borderRadius: 8, padding: '4px 10px',
          fontSize: 12, color: '#a5b4fc', whiteSpace: 'nowrap',
        }}>
          {Math.round((article.score || 0) * 100)}% match
        </div>
      </div>

      {article.abstract && (
        <>
          <div style={{
            fontSize: 13, color: '#94a3b8', lineHeight: 1.6,
            overflow: expanded ? 'visible' : 'hidden',
            maxHeight: expanded ? 'none' : '3.2em',
          }}>
            {article.abstract}
          </div>
          <button
            onClick={() => setExpanded(e => !e)}
            style={{
              background: 'none', border: 'none', color: '#6366f1',
              cursor: 'pointer', fontSize: 12, padding: '4px 0',
            }}
          >{expanded ? 'Show less' : 'Show more'}</button>
        </>
      )}
    </div>
  );
}

export default function SearchResults() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await searchAPI.query(query, 30);
      setResults(res.data);
    } catch (err) {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#a5b4fc' }}>
        Article Search
      </h3>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()}
          placeholder="Search PubMed articles..."
          style={{
            flex: 1, background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 10, padding: '10px 14px', color: '#e2e8f0',
            fontSize: 14, outline: 'none',
          }}
        />
        <button
          onClick={doSearch}
          disabled={loading}
          style={{
            background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
            border: 'none', borderRadius: 10, padding: '10px 20px',
            color: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 500,
          }}
        >{loading ? '...' : 'Search'}</button>
      </div>

      {searched && !loading && results.length === 0 && (
        <div style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>
          No articles found. Try fetching PubMed data first.
        </div>
      )}

      <div>
        {results.map(article => (
          <ArticleCard key={article.pmid} article={article} />
        ))}
      </div>
    </div>
  );
}
