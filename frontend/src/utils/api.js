import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
});

export const chatAPI = {
  send: (message, sessionId) =>
    api.post('/chat/', { message, session_id: sessionId }),
  clearSession: (sessionId) =>
    api.delete(`/chat/${sessionId}`),
  getHistory: (sessionId) =>
    api.get(`/chat/${sessionId}/history`),
};

export const searchAPI = {
  query: (q, topK = 20) =>
    api.get('/search/', { params: { q, top_k: topK } }),
  relationships: (params) =>
    api.get('/search/relationships', { params }),
  network: (params) =>
    api.get('/search/network', { params }),
};

export const articlesAPI = {
  list: (skip = 0, limit = 20) =>
    api.get('/articles/', { params: { skip, limit } }),
  count: () =>
    api.get('/articles/count'),
  get: (pmid) =>
    api.get(`/articles/${pmid}`),
  getRelationships: (pmid) =>
    api.get(`/articles/${pmid}/relationships`),
};

export const ingestAPI = {
  fetchPubmed: (query, maxResults = 1000, runNlp = true) =>
    api.post('/ingest/pubmed', { query, max_results: maxResults, run_nlp: runNlp }),
  getStatus: (jobId) =>
    api.get(`/ingest/status/${jobId}`),
  processArticles: () =>
    api.post('/ingest/process', {}),
  getStats: () =>
    api.get('/ingest/stats'),
};

export default api;
