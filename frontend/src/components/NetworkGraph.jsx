import React, { useState, useCallback, useEffect } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import { searchAPI } from '../utils/api';

const RELATIONSHIP_COLORS = {
  produces: '#10b981',
  consumes: '#f59e0b',
  regulates: '#6366f1',
  inhibits: '#ef4444',
  activates: '#22c55e',
  converts: '#8b5cf6',
  associates_with: '#64748b',
  interacts: '#06b6d4',
};

const stylesheet = [
  {
    selector: 'node[type = "microbe"]',
    style: {
      'background-color': '#6366f1',
      'label': 'data(label)',
      'color': '#fff',
      'font-size': 11,
      'text-valign': 'center',
      'text-halign': 'center',
      'width': 'mapData(mention_count, 1, 50, 40, 80)',
      'height': 'mapData(mention_count, 1, 50, 40, 80)',
      'text-wrap': 'wrap',
      'text-max-width': 80,
      'border-width': 2,
      'border-color': '#818cf8',
    },
  },
  {
    selector: 'node[type = "metabolite"]',
    style: {
      'background-color': '#f59e0b',
      'label': 'data(label)',
      'color': '#1a1a2e',
      'font-size': 10,
      'text-valign': 'center',
      'text-halign': 'center',
      'width': 'mapData(mention_count, 1, 50, 30, 60)',
      'height': 'mapData(mention_count, 1, 50, 30, 60)',
      'text-wrap': 'wrap',
      'text-max-width': 70,
      'shape': 'diamond',
      'border-width': 2,
      'border-color': '#fcd34d',
    },
  },
  {
    selector: 'node:selected',
    style: {
      'border-width': 4,
      'border-color': '#fff',
    },
  },
  {
    selector: 'edge',
    style: {
      'width': 'mapData(confidence, 0, 1, 1, 4)',
      'line-color': 'data(color)',
      'target-arrow-color': 'data(color)',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'label': 'data(label)',
      'font-size': 9,
      'color': '#94a3b8',
      'text-rotation': 'autorotate',
      'opacity': 0.8,
    },
  },
  {
    selector: 'edge:selected',
    style: { opacity: 1, 'width': 4 },
  },
];

function buildCyElements(relationships) {
  const nodes = new Map();
  const edges = [];

  relationships.forEach((rel, i) => {
    const microbeId = `m_${rel.microbe?.replace(/\s+/g, '_')}`;
    const metId = `met_${rel.metabolite?.replace(/\s+/g, '_')}`;

    if (!nodes.has(microbeId)) {
      nodes.set(microbeId, {
        data: {
          id: microbeId,
          label: rel.microbe,
          type: 'microbe',
          mention_count: 1,
        }
      });
    } else {
      nodes.get(microbeId).data.mention_count += 1;
    }

    if (!nodes.has(metId)) {
      nodes.set(metId, {
        data: {
          id: metId,
          label: rel.metabolite,
          type: 'metabolite',
          mention_count: 1,
        }
      });
    } else {
      nodes.get(metId).data.mention_count += 1;
    }

    edges.push({
      data: {
        id: `e_${i}`,
        source: microbeId,
        target: metId,
        label: rel.relationship_type,
        color: RELATIONSHIP_COLORS[rel.relationship_type] || '#64748b',
        confidence: rel.confidence || 0.5,
        relationship_type: rel.relationship_type,
        pmid: rel.pmid,
      }
    });
  });

  return [...nodes.values(), ...edges];
}

export default function NetworkGraph({ relationships: propRelationships }) {
  const [elements, setElements] = useState([]);
  const [selectedElement, setSelectedElement] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filterMicrobe, setFilterMicrobe] = useState('');
  const [filterMetabolite, setFilterMetabolite] = useState('');
  const [cyInstance, setCyInstance] = useState(null);

  // Load from prop relationships (chat-driven)
  useEffect(() => {
    if (propRelationships?.length > 0) {
      setElements(buildCyElements(propRelationships));
    }
  }, [propRelationships]);

  const loadNetwork = useCallback(async () => {
    setLoading(true);
    try {
      const res = await searchAPI.network({
        microbe: filterMicrobe || undefined,
        metabolite: filterMetabolite || undefined,
        min_confidence: 0.3,
        limit: 200,
      });
      const data = res.data;
      const cyElements = [
        ...data.nodes.map(n => ({
          ...n,
          data: { ...n.data, color: RELATIONSHIP_COLORS[n.data.relationship_type] || '#64748b' }
        })),
        ...data.edges.map(e => ({
          ...e,
          data: { ...e.data, color: RELATIONSHIP_COLORS[e.data.relationship_type] || '#64748b' }
        })),
      ];
      setElements(cyElements);
    } catch (err) {
      console.error('Network load error:', err);
    } finally {
      setLoading(false);
    }
  }, [filterMicrobe, filterMetabolite]);

  const handleNodeClick = useCallback((evt) => {
    setSelectedElement(evt.target.data());
  }, []);

  const handleEdgeClick = useCallback((evt) => {
    setSelectedElement(evt.target.data());
  }, []);

  const fitGraph = () => {
    cyInstance?.fit(50);
  };

  const resetLayout = () => {
    cyInstance?.layout({ name: 'cose', animate: true, randomize: false }).run();
  };

  const legendItems = Object.entries(RELATIONSHIP_COLORS).map(([type, color]) => (
    <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
      <div style={{ width: 20, height: 3, background: color, borderRadius: 2 }} />
      <span style={{ fontSize: 11, color: '#94a3b8' }}>{type}</span>
    </div>
  ));

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Controls */}
      <div style={{
        padding: '12px 16px', display: 'flex', gap: 8,
        flexWrap: 'wrap', alignItems: 'center',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
      }}>
        <input
          placeholder="Filter by microbe..."
          value={filterMicrobe}
          onChange={e => setFilterMicrobe(e.target.value)}
          style={inputStyle}
        />
        <input
          placeholder="Filter by metabolite..."
          value={filterMetabolite}
          onChange={e => setFilterMetabolite(e.target.value)}
          style={inputStyle}
        />
        <button onClick={loadNetwork} disabled={loading} style={btnPrimary}>
          {loading ? 'Loading...' : 'Load Network'}
        </button>
        <button onClick={fitGraph} style={btnSecondary}>Fit</button>
        <button onClick={resetLayout} style={btnSecondary}>Re-layout</button>
        <span style={{ marginLeft: 'auto', color: '#64748b', fontSize: 12 }}>
          {elements.filter(e => !e.data?.source).length} nodes ·{' '}
          {elements.filter(e => e.data?.source).length} edges
        </span>
      </div>

      {/* Graph */}
      <div style={{ flex: 1, position: 'relative' }}>
        {elements.length === 0 ? (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            color: '#475569', gap: 12,
          }}>
            <div style={{ fontSize: 48 }}>🔬</div>
            <div style={{ fontSize: 16 }}>No network data yet</div>
            <div style={{ fontSize: 13 }}>
              Ask a question in the chat or click "Load Network"
            </div>
          </div>
        ) : (
          <CytoscapeComponent
            elements={elements}
            stylesheet={stylesheet}
            layout={{ name: 'cose', animate: true, randomize: false, idealEdgeLength: 120 }}
            style={{ width: '100%', height: '100%' }}
            cy={(cy) => {
              setCyInstance(cy);
              cy.on('tap', 'node', handleNodeClick);
              cy.on('tap', 'edge', handleEdgeClick);
            }}
          />
        )}

        {/* Selected element panel */}
        {selectedElement && (
          <div style={{
            position: 'absolute', top: 12, right: 12,
            background: 'rgba(15,23,42,0.95)',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 12, padding: 14, minWidth: 220,
            backdropFilter: 'blur(10px)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#a5b4fc' }}>
                {selectedElement.source ? 'Relationship' : 'Entity'}
              </span>
              <button
                onClick={() => setSelectedElement(null)}
                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >✕</button>
            </div>
            {selectedElement.source ? (
              <>
                <div style={{ fontSize: 13, marginBottom: 4 }}>
                  <span style={{ color: '#a5b4fc' }}>{selectedElement.source.replace('m_', '').replace(/_/g, ' ')}</span>
                  {' → '}
                  <span style={{
                    color: RELATIONSHIP_COLORS[selectedElement.relationship_type] || '#fff',
                    fontWeight: 600,
                  }}>{selectedElement.relationship_type}</span>
                  {' → '}
                  <span style={{ color: '#fcd34d' }}>{selectedElement.target.replace('met_', '').replace(/_/g, ' ')}</span>
                </div>
                <div style={{ fontSize: 12, color: '#64748b' }}>
                  Confidence: {Math.round((selectedElement.confidence || 0) * 100)}%
                </div>
                {selectedElement.pmid && (
                  <div style={{ fontSize: 12, color: '#64748b' }}>PMID: {selectedElement.pmid}</div>
                )}
              </>
            ) : (
              <>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{selectedElement.label}</div>
                <div style={{ fontSize: 12, color: '#64748b' }}>
                  Type: {selectedElement.type} · {selectedElement.entity_type}
                </div>
                {selectedElement.mention_count && (
                  <div style={{ fontSize: 12, color: '#64748b' }}>
                    Mentions: {selectedElement.mention_count}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Legend */}
        <div style={{
          position: 'absolute', bottom: 12, left: 12,
          background: 'rgba(15,23,42,0.85)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 10, padding: '10px 14px',
          backdropFilter: 'blur(8px)',
        }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6, fontWeight: 600 }}>
            RELATIONSHIP TYPES
          </div>
          {legendItems}
          <div style={{ marginTop: 8, borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <div style={{ width: 14, height: 14, borderRadius: '50%', background: '#6366f1' }} />
              <span style={{ fontSize: 11, color: '#94a3b8' }}>Microbe</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 14, height: 14, background: '#f59e0b', transform: 'rotate(45deg)' }} />
              <span style={{ fontSize: 11, color: '#94a3b8', marginLeft: 2 }}>Metabolite</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const inputStyle = {
  background: 'rgba(255,255,255,0.06)',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 8, padding: '6px 12px',
  color: '#e2e8f0', fontSize: 13,
  outline: 'none', minWidth: 160,
};

const btnPrimary = {
  background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
  border: 'none', borderRadius: 8, padding: '6px 16px',
  color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500,
};

const btnSecondary = {
  background: 'rgba(255,255,255,0.06)',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 8, padding: '6px 12px',
  color: '#94a3b8', cursor: 'pointer', fontSize: 13,
};
