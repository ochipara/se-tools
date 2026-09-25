/**
 * setool Architecture Explorer - Cytoscape.js Frontend
 */

// Node Style Definitions matching docs/reading-the-report.md
const NODE_CONFIG = {
  package: { label: 'Package', shape: 'hexagon', color: '#f59e0b', size: 50 },
  module: { label: 'Module', shape: 'rectangle', color: '#eab308', size: 45 },
  distribution: { label: 'Distribution', shape: 'diamond', color: '#ec4899', size: 45 },
  class: { label: 'Class', shape: 'rectangle', color: '#10b981', size: 40 },
  pytorch_module: { label: 'PyTorch Module', shape: 'round-rectangle', color: '#8b5cf6', size: 46 },
  function: { label: 'Function', shape: 'round-rectangle', color: '#06b6d4', size: 36 },
  method: { label: 'Method', shape: 'round-rectangle', color: '#14b8a6', size: 36 },
  value: { label: 'Value', shape: 'ellipse', color: '#64748b', size: 24 },
  call_site: { label: 'Call Site', shape: 'triangle', color: '#94a3b8', size: 22 },
  external_api: { label: 'External API', shape: 'round-rectangle', color: '#f43f5e', size: 38 }
};

// Edge Style Definitions
const EDGE_CONFIG = {
  CALLS: { label: 'CALLS', color: '#ef4444', style: 'solid', width: 2, arrow: 'triangle' },
  CONTAINS: { label: 'CONTAINS', color: '#475569', style: 'dashed', width: 1.5, arrow: 'none' },
  DEPENDS_ON: { label: 'DEPENDS_ON', color: '#f43f5e', style: 'solid', width: 2, arrow: 'triangle' },
  IMPORTS: { label: 'IMPORTS', color: '#3b82f6', style: 'solid', width: 1.8, arrow: 'triangle' },
  INHERITS: { label: 'INHERITS', color: '#10b981', style: 'solid', width: 2, arrow: 'triangle' },
  PASSES_VALUE: { label: 'PASSES_VALUE', color: '#94a3b8', style: 'dotted', width: 1.2, arrow: 'triangle' },
  RETURNS: { label: 'RETURNS', color: '#94a3b8', style: 'dotted', width: 1.2, arrow: 'triangle' },
  INSTANTIATES: { label: 'INSTANTIATES', color: '#a855f7', style: 'solid', width: 1.8, arrow: 'triangle' },
  USES_API: { label: 'USES_API', color: '#ec4899', style: 'solid', width: 1.8, arrow: 'triangle' }
};

// Application State
let cy = null;
let rawGraphData = null;
let rawDependenciesData = null;
let activeNodeFilters = new Set();
let activeEdgeFilters = new Set();
let selectedElement = null;
let activeRegex = '';
let activeDirection = 'both';


// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  initAnalysisUI();
  initEventListeners();
  loadData();
});

async function loadData() {
  const loadingOverlay = document.getElementById('loading-overlay');
  const loadingText = document.getElementById('loading-text');

  try {
    loadingText.textContent = 'Fetching graph data...';
    const graphRes = await fetch('graph.json');
    if (!graphRes.ok) throw new Error(`HTTP ${graphRes.status} loading graph.json`);
    rawGraphData = await graphRes.json();

    try {
      const depRes = await fetch('dependencies.json');
      if (depRes.ok) {
        rawDependenciesData = await depRes.json();
      }
    } catch (e) {
      console.warn('dependencies.json not available', e);
    }

    // Default to 'arch' preset (excludes low-level values/call sites for snappiness)
    setPreset('call_graph');
    initFilters();
    initCycles();
    initCytoscape();

    loadingOverlay.style.opacity = '0';
    setTimeout(() => loadingOverlay.style.display = 'none', 300);
  } catch (err) {
    loadingText.innerHTML = `<span style="color:#ef4444;">Error loading report: ${err.message}</span><br><small style="color:#94a3b8;">Ensure graph.json exists in this report directory.</small>`;
    console.error('Failed to initialize setool UI:', err);
  }
}

function initAnalysisUI() {
  document.getElementById('btn-apply-analysis').addEventListener('click', () => {
    activeRegex = document.getElementById('regex-filter-input').value;
    const dirSelect = document.getElementById('regex-direction-select');
    if (dirSelect) {
      activeDirection = dirSelect.value;
    }
    applyFilters();
  });

  document.getElementById('btn-clear-analysis').addEventListener('click', () => {
    document.getElementById('regex-filter-input').value = '';
    activeRegex = '';
    applyFilters();
  });
}

function setPreset(preset) {
  if (preset === 'call_graph') {
    activeNodeFilters = new Set(['function', 'method']);
    activeEdgeFilters = new Set(['CALLS']);
  }
  updateFilterCheckboxes();
}

function initFilters() {
  const nodeContainer = document.getElementById('node-filters');
  const edgeContainer = document.getElementById('edge-filters');
  nodeContainer.innerHTML = '';
  edgeContainer.innerHTML = '';

  // Count occurrences
  const nodeCounts = {};
  if (rawGraphData && rawGraphData.nodes) {
    Object.values(rawGraphData.nodes).forEach(n => {
      nodeCounts[n.kind] = (nodeCounts[n.kind] || 0) + 1;
    });
  }

  const edgeCounts = {};
  if (rawGraphData && rawGraphData.edges) {
    rawGraphData.edges.forEach(e => {
      edgeCounts[e.kind] = (edgeCounts[e.kind] || 0) + 1;
    });
  }

  // Node Filters
  Object.entries(NODE_CONFIG).forEach(([kind, cfg]) => {
    const count = nodeCounts[kind] || 0;
    if (count === 0 && !activeNodeFilters.has(kind)) return;

    const item = document.createElement('label');
    item.className = 'filter-item';
    item.innerHTML = `
      <div class="filter-left">
        <input type="checkbox" data-kind="${kind}" class="node-filter-cb" ${activeNodeFilters.has(kind) ? 'checked' : ''}>
        <span class="color-dot" style="background-color: ${cfg.color};"></span>
        <span>${cfg.label}</span>
      </div>
      <span class="filter-count">${count}</span>
    `;

    item.querySelector('input').addEventListener('change', (e) => {
      if (e.target.checked) activeNodeFilters.add(kind);
      else activeNodeFilters.delete(kind);
      applyFilters();
    });

    nodeContainer.appendChild(item);
  });

  // Edge Filters
  Object.entries(EDGE_CONFIG).forEach(([kind, cfg]) => {
    const count = edgeCounts[kind] || 0;
    if (count === 0 && !activeEdgeFilters.has(kind)) return;

    const item = document.createElement('label');
    item.className = 'filter-item';
    item.innerHTML = `
      <div class="filter-left">
        <input type="checkbox" data-edge-kind="${kind}" class="edge-filter-cb" ${activeEdgeFilters.has(kind) ? 'checked' : ''}>
        <span class="edge-line-dot" style="background-color: ${cfg.color};"></span>
        <span>${cfg.label}</span>
      </div>
      <span class="filter-count">${count}</span>
    `;

    item.querySelector('input').addEventListener('change', (e) => {
      if (e.target.checked) activeEdgeFilters.add(kind);
      else activeEdgeFilters.delete(kind);
      applyFilters();
    });

    edgeContainer.appendChild(item);
  });
}

function updateFilterCheckboxes() {
  document.querySelectorAll('.node-filter-cb').forEach(cb => {
    cb.checked = activeNodeFilters.has(cb.dataset.kind);
  });
  document.querySelectorAll('.edge-filter-cb').forEach(cb => {
    cb.checked = activeEdgeFilters.has(cb.dataset.edgeKind);
  });
}

function initCycles() {
  const cyclesSection = document.getElementById('cycles-section');
  const cyclesCount = document.getElementById('cycles-count');
  const metricCycles = document.getElementById('metric-cycles');
  const cyclesList = document.getElementById('cycles-list');

  const cycles = (rawDependenciesData && rawDependenciesData.cycles) || [];
  metricCycles.textContent = cycles.length;

  if (cycles.length > 0) {
    cyclesSection.style.display = 'flex';
    cyclesCount.textContent = cycles.length;
    cyclesList.innerHTML = '';

    cycles.forEach((cycle, idx) => {
      const card = document.createElement('div');
      card.className = 'cycle-card';
      card.innerHTML = `
        <div class="cycle-title">Cycle #${idx + 1} (${cycle.length} components)</div>
        <div class="cycle-members">${cycle.join(' &rarr; ')}</div>
      `;
      card.addEventListener('click', () => highlightCycle(cycle));
      cyclesList.appendChild(card);
    });
  } else {
    cyclesSection.style.display = 'none';
  }
}

function highlightCycle(cycleMembers) {
  if (!cy) return;
  cy.elements().removeClass('highlighted-cycle dimmed');

  const cycleSet = new Set(cycleMembers);
  const matchedNodes = cy.nodes().filter(n => cycleSet.has(n.data('id')) || cycleSet.has(n.data('name')));

  if (matchedNodes.length === 0) {
    // Re-enable node filters to show packages/modules if needed
    activeNodeFilters.add('package');
    activeNodeFilters.add('module');
    updateFilterCheckboxes();
    applyFilters();
  }

  cy.elements().addClass('dimmed');
  matchedNodes.removeClass('dimmed').addClass('highlighted-cycle');
  matchedNodes.connectedEdges().forEach(edge => {
    if (cycleSet.has(edge.source().id()) && cycleSet.has(edge.target().id())) {
      edge.removeClass('dimmed').addClass('highlighted-cycle');
    }
  });

  cy.animate({
    fit: { eles: matchedNodes, padding: 60 },
    duration: 500
  });
}

// Register Cytoscape plugins if available in browser
if (typeof cytoscapeDagre !== 'undefined' && typeof cytoscape !== 'undefined') {
  try {
    cytoscape.use(cytoscapeDagre);
  } catch (e) {
    console.warn('cytoscape-dagre registration warning:', e);
  }
}

function initCytoscape() {
  const elements = prepareElements();

  // Metrics
  document.getElementById('metric-nodes').textContent = Object.keys(rawGraphData.nodes || {}).length;
  document.getElementById('metric-edges').textContent = (rawGraphData.edges || []).length;
  document.getElementById('metric-visible').textContent = elements.nodes.length;

  // Cytoscape styles matching specs
  const styles = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'color': '#f8fafc',
        'font-family': 'Inter, sans-serif',
        'font-size': '11px',
        'text-valign': 'center',
        'text-halign': 'center',
        'text-outline-color': '#090d16',
        'text-outline-width': 2,
        'background-color': 'data(color)',
        'shape': 'data(shape)',
        'width': 'data(size)',
        'height': 'data(size)',
        'border-width': 1.5,
        'border-color': 'rgba(255, 255, 255, 0.2)',
        'transition-property': 'background-color, border-color, opacity',
        'transition-duration': '0.2s'
      }
    },
    {
      selector: 'node[kind = "pytorch_module"]',
      style: {
        'border-width': 2.5,
        'border-color': '#c084fc',
        'font-weight': '600'
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 'data(width)',
        'line-color': 'data(color)',
        'line-style': 'data(style)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'data(arrow)',
        'curve-style': 'bezier',
        'arrow-scale': 1.1,
        'opacity': 0.7,
        'transition-property': 'opacity, width, line-color',
        'transition-duration': '0.2s'
      }
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 3,
        'border-color': '#ffffff',
        'underlay-color': '#6366f1',
        'underlay-padding': 6,
        'underlay-opacity': 0.5
      }
    },
    {
      selector: 'edge:selected',
      style: {
        'width': 3.5,
        'opacity': 1,
        'line-color': '#ffffff',
        'target-arrow-color': '#ffffff'
      }
    },
    {
      selector: '.highlighted',
      style: {
        'opacity': 1,
        'border-color': '#38bdf8',
        'border-width': 3,
        'underlay-color': '#38bdf8',
        'underlay-padding': 6,
        'underlay-opacity': 0.5
      }
    },
    {
      selector: '.highlighted-cycle',
      style: {
        'opacity': 1,
        'border-color': '#fbbf24',
        'line-color': '#fbbf24',
        'target-arrow-color': '#fbbf24',
        'border-width': 3,
        'underlay-color': '#fbbf24',
        'underlay-padding': 8,
        'underlay-opacity': 0.6
      }
    },
    {
      selector: '.dimmed',
      style: {
        'opacity': 0.12
      }
    }
  ];

  const initialLayoutName = document.getElementById('layout-select').value || 'concentric';
  cy = cytoscape({
    container: document.getElementById('cy'),
    elements: [...elements.nodes, ...elements.edges],
    style: styles,
    layout: getLayoutConfig(initialLayoutName),
    minZoom: 0.02,
    maxZoom: 5
  });

  setTimeout(() => {
    if (cy) {
      cy.resize();
      cy.fit(undefined, 40);
    }
  }, 100);

  // Cytoscape interaction events
  cy.on('tap', 'node', (evt) => {
    inspectNode(evt.target);
  });

  cy.on('tap', 'edge', (evt) => {
    inspectEdge(evt.target);
  });

  cy.on('tap', (evt) => {
    if (evt.target === cy) {
      clearSelection();
    }
  });
}

function prepareElements() {
  const nodes = [];
  const edges = [];
  const addedNodes = new Set();

  if (!rawGraphData || !rawGraphData.nodes) {
    return { nodes, edges };
  }

  // 1. Initial pass: Apply node filters and optionally the regex filter
  let candidateNodes = new Set();
  let regex = null;

  if (activeRegex.trim() !== '') {
    try {
      regex = new RegExp(activeRegex.trim());
    } catch (e) {
      console.warn("Invalid regex", e);
    }
  }

  const matchesRegex = (n) => {
    if (!regex) return true;
    return regex.test(n.id) || (n.name && regex.test(n.name));
  };

  const validNodes = new Set();
  Object.values(rawGraphData.nodes).forEach(n => {
    if (activeNodeFilters.has(n.kind)) {
      validNodes.add(n.id);
      if (matchesRegex(n)) {
        candidateNodes.add(n.id);
      }
    }
  });

  // 2. Reachability expansion if regex is active
  if (regex && candidateNodes.size > 0 && candidateNodes.size < validNodes.size) {
    // Build adjacency list for current edge filters
    const adjForward = new Map();
    const adjBackward = new Map();

    (rawGraphData.edges || []).forEach(e => {
      if (!activeEdgeFilters.has(e.kind)) return;
      if (!validNodes.has(e.source) || !validNodes.has(e.target)) return;

      if (!adjForward.has(e.source)) adjForward.set(e.source, []);
      adjForward.get(e.source).push(e.target);

      if (!adjBackward.has(e.target)) adjBackward.set(e.target, []);
      adjBackward.get(e.target).push(e.source);
    });

    const reachableNodes = new Set(candidateNodes);

    if (activeDirection === 'forward' || activeDirection === 'both') {
      // BFS Forward (descendants)
      let queue = Array.from(candidateNodes);
      let visitedForward = new Set(candidateNodes);
      while (queue.length > 0) {
        const current = queue.shift();
        const neighbors = adjForward.get(current) || [];
        for (const neighbor of neighbors) {
          if (!visitedForward.has(neighbor)) {
            visitedForward.add(neighbor);
            reachableNodes.add(neighbor);
            queue.push(neighbor);
          }
        }
      }
    }

    if (activeDirection === 'backward' || activeDirection === 'both') {
      // BFS Backward (ancestors)
      let queue = Array.from(candidateNodes);
      let visitedBackward = new Set(candidateNodes);
      while (queue.length > 0) {
        const current = queue.shift();
        const neighbors = adjBackward.get(current) || [];
        for (const neighbor of neighbors) {
          if (!visitedBackward.has(neighbor)) {
            visitedBackward.add(neighbor);
            reachableNodes.add(neighbor);
            queue.push(neighbor);
          }
        }
      }
    }

    candidateNodes = reachableNodes;
  } else if (!regex) {
    candidateNodes = validNodes;
  } else if (regex && candidateNodes.size === 0) {
    candidateNodes = new Set();
  }

  // 3. Build final Cytoscape elements
  Object.values(rawGraphData.nodes).forEach(n => {
    if (candidateNodes.has(n.id)) {
      const cfg = NODE_CONFIG[n.kind] || { shape: 'round-rectangle', color: '#94a3b8', size: 30 };
      nodes.push({
        data: {
          id: n.id,
          label: n.name || n.id.split('.').pop() || n.id,
          kind: n.kind,
          color: cfg.color,
          shape: cfg.shape,
          size: cfg.size,
          raw: n
        }
      });
      addedNodes.add(n.id);
    }
  });

  // Filter edges (only between currently visible nodes)
  (rawGraphData.edges || []).forEach((e, idx) => {
    if (!activeEdgeFilters.has(e.kind)) return;
    if (!addedNodes.has(e.source) || !addedNodes.has(e.target)) return;

    const cfg = EDGE_CONFIG[e.kind] || { color: '#64748b', style: 'solid', width: 1.5, arrow: 'triangle' };
    edges.push({
      data: {
        id: `e_${idx}_${e.source}_${e.target}`,
        source: e.source,
        target: e.target,
        kind: e.kind,
        color: cfg.color,
        style: cfg.style,
        width: cfg.width,
        arrow: cfg.arrow,
        raw: e
      }
    });
  });

  return { nodes, edges };
}

function applyFilters() {
  if (!cy) return;
  const elements = prepareElements();
  cy.elements().remove();
  cy.add([...elements.nodes, ...elements.edges]);

  document.getElementById('metric-visible').textContent = elements.nodes.length;
  runLayout();
}

function getLayoutConfig(layoutName) {
  if (layoutName === 'concentric') {
    return {
      name: 'concentric',
      concentric: function(node) {
        const kind = node.data('kind');
        if (kind === 'package') return 70;
        if (kind === 'distribution') return 60;
        if (kind === 'module') return 50;
        if (kind === 'pytorch_module') return 40;
        if (kind === 'class') return 30;
        if (kind === 'function' || kind === 'method') return 20;
        return 10;
      },
      levelWidth: function() { return 10; },
      padding: 50,
      fit: true,
      animate: false
    };
  }
  if (layoutName === 'breadthfirst') {
    return {
      name: 'breadthfirst',
      directed: true,
      padding: 50,
      spacingFactor: 1.25,
      fit: true,
      animate: false
    };
  }
  if (layoutName === 'dagre') {
    return {
      name: 'dagre',
      rankDir: 'TB',
      nodeSep: 60,
      rankSep: 100,
      padding: 50,
      fit: true,
      animate: false
    };
  }
  if (layoutName === 'cose') {
    return {
      name: 'cose',
      idealEdgeLength: 80,
      nodeOverlap: 20,
      refresh: 20,
      fit: true,
      padding: 40,
      randomize: false,
      componentSpacing: 100,
      nodeRepulsion: 600000,
      edgeElasticity: 100,
      nestingFactor: 5,
      gravity: 80,
      numIter: 400,
      animate: false
    };
  }
  return {
    name: layoutName,
    padding: 50,
    fit: true,
    animate: false
  };
}

function runLayout() {
  if (!cy) return;
  const layoutName = document.getElementById('layout-select').value;
  try {
    const layout = cy.layout(getLayoutConfig(layoutName));
    layout.run();
    setTimeout(() => {
      if (cy) cy.fit(undefined, 40);
    }, 50);
  } catch (err) {
    console.warn(`Layout '${layoutName}' failed, falling back to concentric:`, err);
    const fallbackLayout = cy.layout(getLayoutConfig('concentric'));
    fallbackLayout.run();
    setTimeout(() => {
      if (cy) cy.fit(undefined, 40);
    }, 50);
  }
}

// Inspector logic
function inspectNode(node) {
  selectedElement = node;
  cy.elements().removeClass('highlighted dimmed');

  // Highlight 1-hop neighborhood
  const neighborhood = node.neighborhood().add(node);
  cy.elements().addClass('dimmed');
  neighborhood.removeClass('dimmed').addClass('highlighted');

  const data = node.data('raw');
  const cfg = NODE_CONFIG[data.kind] || { label: data.kind, color: '#64748b' };

  const panel = document.getElementById('inspector-content');
  const inEdges = node.incomers('edge');
  const outEdges = node.outgoers('edge');

  let locationHtml = '';
  if (data.location) {
    locationHtml = `
      <div class="detail-section">
        <span class="detail-label">Location</span>
        <div class="detail-box">
          ${escapeHtml(data.location.file)}<br>
          <span style="color:#38bdf8;">Lines ${data.location.line_start} &ndash; ${data.location.line_end}</span>
        </div>
      </div>
    `;
  }

  let typeHtml = '';
  if (data.python_type && data.python_type.raw) {
    typeHtml = `
      <div class="detail-section">
        <span class="detail-label">Python Type</span>
        <div class="detail-box" style="color:#a855f7;">${escapeHtml(data.python_type.raw)}</div>
      </div>
    `;
  }

  let incomersHtml = '';
  if (inEdges.length > 0) {
    incomersHtml = `
      <div class="detail-section">
        <span class="detail-label">Incoming Connections (${inEdges.length})</span>
        <div class="neighbor-list">
          ${inEdges.map(e => `
            <div class="neighbor-item" onclick="focusNode('${escapeHtml(e.source().id())}')">
              <span class="badge" style="background:${EDGE_CONFIG[e.data('kind')]?.color || '#64748b'}; color:#fff; font-size:9px;">${e.data('kind')}</span>
              <span class="neighbor-id">${escapeHtml(e.source().data('label'))}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  let outgoersHtml = '';
  if (outEdges.length > 0) {
    outgoersHtml = `
      <div class="detail-section">
        <span class="detail-label">Outgoing Connections (${outEdges.length})</span>
        <div class="neighbor-list">
          ${outEdges.map(e => `
            <div class="neighbor-item" onclick="focusNode('${escapeHtml(e.target().id())}')">
              <span class="badge" style="background:${EDGE_CONFIG[e.data('kind')]?.color || '#64748b'}; color:#fff; font-size:9px;">${e.data('kind')}</span>
              <span class="neighbor-id">${escapeHtml(e.target().data('label'))}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  panel.innerHTML = `
    <div class="node-header-card">
      <span class="badge" style="background:${cfg.color}; color:#fff;">${cfg.label}</span>
      <div class="detail-id">${escapeHtml(data.id)}</div>
    </div>
    ${locationHtml}
    ${typeHtml}
    ${incomersHtml}
    ${outgoersHtml}
  `;
}

function inspectEdge(edge) {
  selectedElement = edge;
  cy.elements().removeClass('highlighted dimmed');

  edge.connectedNodes().add(edge).removeClass('dimmed').addClass('highlighted');

  const data = edge.data('raw');
  const cfg = EDGE_CONFIG[data.kind] || { color: '#64748b' };
  const panel = document.getElementById('inspector-content');

  let provHtml = '';
  if (data.provenance && data.provenance.length > 0) {
    provHtml = `
      <div class="detail-section">
        <span class="detail-label">Provenance</span>
        <div class="detail-box">${data.provenance.map(p => escapeHtml(p)).join(', ')}</div>
      </div>
    `;
  }

  panel.innerHTML = `
    <div class="node-header-card">
      <span class="badge" style="background:${cfg.color}; color:#fff;">${data.kind}</span>
      <div class="detail-id" style="font-size:12px;">${escapeHtml(data.source)} &rarr; ${escapeHtml(data.target)}</div>
    </div>
    <div class="detail-section">
      <span class="detail-label">Source Node</span>
      <div class="detail-box" style="cursor:pointer;" onclick="focusNode('${escapeHtml(data.source)}')">${escapeHtml(data.source)}</div>
    </div>
    <div class="detail-section">
      <span class="detail-label">Target Node</span>
      <div class="detail-box" style="cursor:pointer;" onclick="focusNode('${escapeHtml(data.target)}')">${escapeHtml(data.target)}</div>
    </div>
    ${provHtml}
  `;
}

function clearSelection() {
  selectedElement = null;
  if (cy) {
    cy.elements().removeClass('highlighted highlighted-cycle dimmed');
  }
  document.getElementById('inspector-content').innerHTML = `
    <div class="empty-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="16" x2="12" y2="12"></line>
        <line x1="12" y1="8" x2="12.01" y2="8"></line>
      </svg>
      <p>Select any node or edge on the canvas to inspect its metadata, location, types, and connections.</p>
    </div>
  `;
}

window.focusNode = function(nodeId) {
  if (!cy) return;
  const node = cy.getElementById(nodeId);
  if (node && node.length > 0) {
    cy.animate({
      center: { eles: node },
      zoom: 1.5,
      duration: 400
    });
    inspectNode(node);
  } else {
    // If not visible due to filters, find in raw data and enable kind
    if (rawGraphData && rawGraphData.nodes && rawGraphData.nodes[nodeId]) {
      const kind = rawGraphData.nodes[nodeId].kind;
      activeNodeFilters.add(kind);
      updateFilterCheckboxes();
      applyFilters();
      setTimeout(() => focusNode(nodeId), 200);
    }
  }
};

function initEventListeners() {
  // Zoom & Fit Controls
  document.getElementById('btn-fit').addEventListener('click', () => {
    if (cy) cy.animate({ fit: { padding: 40 }, duration: 400 });
  });

  document.getElementById('btn-zoom-in').addEventListener('click', () => {
    if (cy) cy.zoom({ level: cy.zoom() * 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  });

  document.getElementById('btn-zoom-out').addEventListener('click', () => {
    if (cy) cy.zoom({ level: cy.zoom() * 0.7, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  });

  document.getElementById('layout-select').addEventListener('change', () => {
    runLayout();
  });

  document.getElementById('btn-re-layout').addEventListener('click', () => {
    runLayout();
  });

  document.getElementById('btn-reset-filters').addEventListener('click', () => {
    setPreset('call_graph');
    applyFilters();
  });

  document.getElementById('btn-close-inspector').addEventListener('click', () => {
    clearSelection();
  });

  // Search input and dropdown
  const searchInput = document.getElementById('search-input');
  const searchDropdown = document.getElementById('search-dropdown');
  const searchClear = document.getElementById('search-clear');

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim().toLowerCase();
    searchClear.style.display = query ? 'block' : 'none';

    if (!query || !rawGraphData || !rawGraphData.nodes) {
      searchDropdown.style.display = 'none';
      return;
    }

    const matches = Object.values(rawGraphData.nodes).filter(n => {
      return n.id.toLowerCase().includes(query) || (n.name && n.name.toLowerCase().includes(query));
    }).slice(0, 20);

    if (matches.length === 0) {
      searchDropdown.innerHTML = '<div class="search-item" style="color:#64748b;">No matching symbols found</div>';
    } else {
      searchDropdown.innerHTML = matches.map(m => `
        <div class="search-item" onclick="focusNode('${escapeHtml(m.id)}'); document.getElementById('search-dropdown').style.display='none';">
          <span class="search-item-id">${escapeHtml(m.name || m.id)}</span>
          <span class="badge" style="background:${NODE_CONFIG[m.kind]?.color || '#64748b'}; color:#fff; font-size:9px;">${m.kind}</span>
        </div>
      `).join('');
    }
    searchDropdown.style.display = 'block';
  });

  searchClear.addEventListener('click', () => {
    searchInput.value = '';
    searchClear.style.display = 'none';
    searchDropdown.style.display = 'none';
    searchInput.focus();
  });

  // Keyboard shortcut '/' to search
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== searchInput) {
      e.preventDefault();
      searchInput.focus();
    } else if (e.key === 'Escape') {
      searchDropdown.style.display = 'none';
      clearSelection();
    }
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) {
      searchDropdown.style.display = 'none';
    }
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
