import React, { useState, useEffect, useCallback } from 'react';
import { ingestAPI } from '../utils/api';

export default function IngestPanel({ onStatsUpdate }) {
  const [query, setQuery] = useState('microbe metabolite');
  const [maxResults, setMaxResults] = useState(1000);
  const [runNlp, setRunNlp] = useState(true);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadStats = useCallback(async () => {
    try {
      const res = await ingestAPI.getStats();
      setStats(res.data);
      if (onStatsUpdate) onStatsUpdate(res.data);
    } catch {}
  }, [onStatsUpdate]);

  useEffect(() => { loadStats(); }, [loadStats]);

  // Poll job status
  useEffect(() => {
    if (!jobId || jobStatus?.status === 'completed' || jobStatus?.status === 'failed') return;
    const interval = setInterval(async () => {
      try {
        const res = await ingestAPI.getStatus(jobId);
        setJobStatus(res.data);
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          clearInterval(interval);
          loadStats();
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [jobId, jobStatus?.status, loadStats]);

  const startIngestion = async () => {
    setLoading(true);
    setJobStatus(null);
    try {
      const res = await ingestAPI.fetchPubmed(query, maxResults, runNlp);
      setJobId(res.data.job_id);
      setJobStatus({ status: 'queued' });
    } catch (err) {
      setJobStatus({ status: 'failed', error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const processArticles = async () => {
    setLoading(true);
    try {
      const res = await ingestAPI.processArticles();
      setJobId(res.data.job_id);
      setJobStatus({ status: 'queued' });
    } catch (err) {
      setJobStatus({ status: 'failed', error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const statusColor = {
    queued: '#94a3b8',
    fetching: '#6366f1',
    extracting_entities: '#8b5cf6',
    computing_embeddings: '#06b6d4',
    completed: '#10b981',
    failed: '#ef4444',
    processing: '#f59e0b',
  };

  return (
    <div style={{ padding: 20 }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#a5b4fc' }}>
        Data Ingestion
      </h3>

      {/* Stats */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10, marginBottom: 20 }}>
          {[
            { label: 'Articles', value: stats.articles },
            { label: 'Processed', value: stats.articles_processed },
            { label: 'Microbes', value: stats.microbes },
            { label: 'Metabolites', value: stats.metabolites },
            { label: 'Relationships', value: stats.relationships },
          ].map(item => (
            <div key={item.label} style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 10, padding: '10px 14px',
            }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>
                {(item.value || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: 12, color: '#64748b' }}>{item.label}</div>
            </div>
          ))}
          <button
            onClick={loadStats}
            style={{
              background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 10, padding: '10px 14px', color: '#64748b',
              cursor: 'pointer', fontSize: 12,
            }}
          >↻ Refresh</button>
        </div>
      )}

      {/* Fetch form */}
      <div style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 12, padding: 16, marginBottom: 16,
      }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: '#94a3b8' }}>
          Fetch PubMed Articles
        </div>
        <div style={{ marginBottom: 10 }}>
          <label style={labelStyle}>Search Query</label>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            style={inputStyle}
          />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label style={labelStyle}>Max Results (1–5000)</label>
          <input
            type="number" min="1" max="5000"
            value={maxResults}
            onChange={e => setMaxResults(Number(e.target.value))}
            style={{ ...inputStyle, width: 120 }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <input
            type="checkbox" id="runNlp"
            checked={runNlp}
            onChange={e => setRunNlp(e.target.checked)}
          />
          <label htmlFor="runNlp" style={{ fontSize: 13, color: '#94a3b8' }}>
            Run NLP pipeline after fetch
          </label>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={startIngestion} disabled={loading} style={btnPrimary}>
            {loading ? 'Starting...' : 'Fetch Articles'}
          </button>
          <button onClick={processArticles} disabled={loading} style={btnSecondary}>
            Process Unprocessed
          </button>
        </div>
      </div>

      {/* Job status */}
      {jobStatus && (
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          border: `1px solid ${statusColor[jobStatus.status] || '#334155'}`,
          borderRadius: 12, padding: 14,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: statusColor[jobStatus.status] || '#64748b',
              animation: ['queued', 'fetching', 'extracting_entities', 'computing_embeddings', 'processing']
                .includes(jobStatus.status) ? 'pulse 1.5s infinite' : 'none',
            }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: statusColor[jobStatus.status] }}>
              {jobStatus.status?.replace(/_/g, ' ').toUpperCase()}
            </span>
          </div>
          {jobStatus.articles_fetched !== undefined && (
            <div style={{ fontSize: 12, color: '#64748b' }}>
              Articles fetched: {jobStatus.articles_fetched}
            </div>
          )}
          {jobStatus.relationships_extracted !== undefined && (
            <div style={{ fontSize: 12, color: '#64748b' }}>
              Relationships: {jobStatus.relationships_extracted}
            </div>
          )}
          {jobStatus.embeddings_computed !== undefined && (
            <div style={{ fontSize: 12, color: '#64748b' }}>
              Embeddings: {jobStatus.embeddings_computed}
            </div>
          )}
          {jobStatus.error && (
            <div style={{ fontSize: 12, color: '#ef4444', marginTop: 4 }}>
              Error: {jobStatus.error}
            </div>
          )}
        </div>
      )}

      {/* Example queries */}
      <div style={{ marginTop: 20 }}>
        <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>Quick fetch queries:</div>
        {[
          'gut microbiome butyrate',
          'Lactobacillus metabolites',
          'microbial secondary metabolites',
          'bacteria bile acid',
        ].map(q => (
          <button
            key={q}
            onClick={() => setQuery(q)}
            style={{
              display: 'block', width: '100%', textAlign: 'left',
              background: 'none', border: 'none',
              color: '#6366f1', cursor: 'pointer',
              fontSize: 12, padding: '4px 0',
            }}
          >→ {q}</button>
        ))}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}

const labelStyle = { display: 'block', fontSize: 12, color: '#64748b', marginBottom: 4 };
const inputStyle = {
  width: '100%', background: 'rgba(255,255,255,0.06)',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 8, padding: '8px 12px', color: '#e2e8f0',
  fontSize: 13, outline: 'none',
};
const btnPrimary = {
  background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
  border: 'none', borderRadius: 8, padding: '8px 18px',
  color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500,
};
const btnSecondary = {
  background: 'rgba(255,255,255,0.06)',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 8, padding: '8px 14px',
  color: '#94a3b8', cursor: 'pointer', fontSize: 13,
};
