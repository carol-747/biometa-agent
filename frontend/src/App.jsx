import React, { useState } from 'react';
import ChatInterface from './components/ChatInterface';
import NetworkGraph from './components/NetworkGraph';
import IngestPanel from './components/IngestPanel';
import SearchResults from './components/SearchResults';

const TABS = ['Chat', 'Network', 'Search', 'Ingest'];

export default function App() {
  const [activeTab, setActiveTab] = useState('Chat');
  const [networkRelationships, setNetworkRelationships] = useState([]);
  const [stats, setStats] = useState(null);

  const handleNetworkData = (relationships) => {
    setNetworkRelationships(relationships);
    // Auto-switch to network tab when data arrives
    // setActiveTab('Network');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{
        background: 'rgba(255,255,255,0.03)',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        padding: '0 24px',
        display: 'flex', alignItems: 'center', gap: 24, height: 60,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18,
          }}>🔬</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#e2e8f0' }}>BiometaAgent</div>
            <div style={{ fontSize: 11, color: '#64748b' }}>Microbe-Metabolite Explorer</div>
          </div>
        </div>

        {/* Tab nav */}
        <nav style={{ display: 'flex', gap: 4, marginLeft: 20 }}>
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                background: activeTab === tab
                  ? 'rgba(99,102,241,0.2)'
                  : 'transparent',
                border: activeTab === tab
                  ? '1px solid rgba(99,102,241,0.4)'
                  : '1px solid transparent',
                borderRadius: 8, padding: '6px 16px',
                color: activeTab === tab ? '#a5b4fc' : '#64748b',
                cursor: 'pointer', fontSize: 13, fontWeight: 500,
                transition: 'all 0.15s',
              }}
            >{tab}</button>
          ))}
        </nav>

        {/* Stats chips */}
        {stats && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
            {[
              { label: 'Articles', value: stats.articles },
              { label: 'Microbes', value: stats.microbes },
              { label: 'Metabolites', value: stats.metabolites },
              { label: 'Relationships', value: stats.relationships },
            ].map(item => (
              <div key={item.label} style={{
                fontSize: 12, color: '#94a3b8',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 20, padding: '3px 12px',
              }}>
                <span style={{ fontWeight: 600, color: '#e2e8f0' }}>
                  {(item.value || 0).toLocaleString()}
                </span>{' '}
                {item.label}
              </div>
            ))}
          </div>
        )}
      </header>

      {/* Main content */}
      <main style={{ flex: 1, display: 'flex', overflow: 'hidden', height: 'calc(100vh - 60px)' }}>
        {/* Chat + Network side by side on Chat tab */}
        {activeTab === 'Chat' && (
          <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
            <div style={{
              width: 480, flexShrink: 0,
              borderRight: '1px solid rgba(255,255,255,0.08)',
              display: 'flex', flexDirection: 'column', overflow: 'hidden',
            }}>
              <ChatInterface onNetworkData={handleNetworkData} />
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <NetworkGraph relationships={networkRelationships} />
            </div>
          </div>
        )}

        {activeTab === 'Network' && (
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <NetworkGraph relationships={networkRelationships} />
          </div>
        )}

        {activeTab === 'Search' && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <SearchResults />
          </div>
        )}

        {activeTab === 'Ingest' && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <IngestPanel onStatsUpdate={setStats} />
          </div>
        )}
      </main>
    </div>
  );
}
