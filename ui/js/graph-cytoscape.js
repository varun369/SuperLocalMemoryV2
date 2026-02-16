// SuperLocalMemory V2.6.5 - Interactive Knowledge Graph (Cytoscape.js)
// Copyright (c) 2026 Varun Pratap Bhardwaj — MIT License
// Replaces D3.js force-directed graph with Cytoscape.js for interactive exploration

var cy = null; // Cytoscape.js instance (global)
var graphData = { nodes: [], links: [] }; // Raw data from API
var originalGraphData = { nodes: [], links: [] }; // Unfiltered data (for reset)
var currentLayout = 'fcose'; // Default layout
var filterState = { cluster_id: null, entity: null }; // Current filters
var isInitialLoad = true; // Track if this is the first graph load
var focusedNodeIndex = 0; // Keyboard navigation: currently focused node
var keyboardNavigationEnabled = false; // Track if keyboard nav is active
var lastFocusedElement = null; // Store last focused element for modal return

// Cluster colors (match Clusters tab)
const CLUSTER_COLORS = [
    '#667eea', '#764ba2', '#43e97b', '#38f9d7',
    '#4facfe', '#00f2fe', '#f093fb', '#f5576c',
    '#fa709a', '#fee140', '#30cfd0', '#330867'
];

function getClusterColor(cluster_id) {
    if (!cluster_id) return '#999';
    return CLUSTER_COLORS[cluster_id % CLUSTER_COLORS.length];
}

// HTML escape utility (prevent XSS)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Load graph data from API
async function loadGraph() {
    var maxNodes = document.getElementById('graph-max-nodes').value;
    var minImportance = document.getElementById('graph-min-importance')?.value || 1;

    // Get cluster filter from URL params ONLY on initial load
    // After that, use filterState (which tab event handler controls)
    if (isInitialLoad) {
        const urlParams = new URLSearchParams(window.location.search);
        const clusterIdParam = urlParams.get('cluster_id');
        if (clusterIdParam) {
            filterState.cluster_id = parseInt(clusterIdParam);
            console.log('[loadGraph] Initial load with cluster filter from URL:', filterState.cluster_id);
        }
        isInitialLoad = false;
    }

    // CRITICAL FIX: When filtering by cluster, fetch MORE nodes to ensure all cluster members are included
    // Otherwise only top N memories are fetched and cluster filter fails
    const fetchLimit = filterState.cluster_id ? 200 : maxNodes;
    console.log('[loadGraph] Fetching with limit:', fetchLimit, 'Cluster filter:', filterState.cluster_id);

    try {
        showLoadingSpinner();
        const response = await fetch(`/api/graph?max_nodes=${fetchLimit}&min_importance=${minImportance}`);
        graphData = await response.json();
        originalGraphData = JSON.parse(JSON.stringify(graphData)); // Deep copy

        // Apply filters if set
        if (filterState.cluster_id) {
            graphData = filterByCluster(originalGraphData, filterState.cluster_id);
        }
        if (filterState.entity) {
            graphData = filterByEntity(originalGraphData, filterState.entity);
        }

        renderGraph(graphData);
        hideLoadingSpinner();
    } catch (error) {
        console.error('Error loading graph:', error);
        showError('Failed to load graph. Please try again.');
        hideLoadingSpinner();
    }
}

// Filter graph by cluster
function filterByCluster(data, cluster_id) {
    console.log('[filterByCluster] Filtering for cluster_id:', cluster_id, 'Type:', typeof cluster_id);
    console.log('[filterByCluster] Total nodes in data:', data.nodes.length);

    // Convert to integer for comparison
    const targetClusterId = parseInt(cluster_id);
    let debugCount = 0;

    const filteredNodes = data.nodes.filter(n => {
        // Convert node cluster_id to integer for comparison
        const nodeClusterId = n.cluster_id ? parseInt(n.cluster_id) : null;

        // Log first 3 nodes to debug
        if (debugCount < 3) {
            console.log('[filterByCluster] Sample node:', {
                id: n.id,
                cluster_id: n.cluster_id,
                type: typeof n.cluster_id,
                parsed: nodeClusterId,
                match: nodeClusterId === targetClusterId
            });
            debugCount++;
        }

        // Use strict equality after type conversion
        return nodeClusterId === targetClusterId;
    });

    console.log('[filterByCluster] Filtered to', filteredNodes.length, 'nodes');

    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredLinks = data.links.filter(l =>
        nodeIds.has(l.source) && nodeIds.has(l.target)
    );

    console.log('[filterByCluster] Found', filteredLinks.length, 'edges between filtered nodes');

    return { nodes: filteredNodes, links: filteredLinks, clusters: data.clusters };
}

// Filter graph by entity
function filterByEntity(data, entity) {
    const filteredNodes = data.nodes.filter(n => {
        if (n.entities && Array.isArray(n.entities)) {
            return n.entities.includes(entity);
        }
        if (n.tags && n.tags.includes(entity)) {
            return true;
        }
        return false;
    });
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredLinks = data.links.filter(l =>
        nodeIds.has(l.source) && nodeIds.has(l.target)
    );
    return { nodes: filteredNodes, links: filteredLinks, clusters: data.clusters };
}

// Clear all filters
function clearGraphFilters() {
    console.log('[clearGraphFilters] Clearing all filters and reloading full graph');

    // Clear filter state
    filterState = { cluster_id: null, entity: null };

    // CRITICAL: Clear URL completely - remove ?cluster_id=X from address bar
    const cleanUrl = window.location.origin + window.location.pathname;
    window.history.replaceState({}, '', cleanUrl);
    console.log('[clearGraphFilters] URL cleaned to:', cleanUrl);

    // CRITICAL: Clear saved layout positions so nodes don't stay in corner
    // When switching from filtered to full graph, we want fresh layout
    localStorage.removeItem('slm_graph_layout');
    console.log('[clearGraphFilters] Cleared saved layout positions');

    // Reload full graph from API (respects dropdown settings)
    loadGraph();
}

// Update filter badge UI - CLEAR status for users
function updateFilterBadge() {
    const statusFull = document.getElementById('graph-status-full');
    const statusFiltered = document.getElementById('graph-status-filtered');
    const filterDescription = document.getElementById('graph-filter-description');
    const filterCount = document.getElementById('graph-filter-count');
    const statusFullText = document.getElementById('graph-status-full-text');

    const hasFilter = filterState.cluster_id || filterState.entity;

    if (hasFilter) {
        // FILTERED STATE - Show prominent alert with "Show All Memories" button
        if (statusFull) statusFull.style.display = 'none';
        if (statusFiltered) statusFiltered.style.display = 'block';

        // Update filter description
        if (filterDescription) {
            const text = filterState.cluster_id
                ? `Viewing Cluster ${filterState.cluster_id}`
                : `Viewing: ${filterState.entity}`;
            filterDescription.textContent = text;
        }

        // Update count (will be set after graph renders)
        if (filterCount && graphData && graphData.nodes) {
            filterCount.textContent = `(${graphData.nodes.length} ${graphData.nodes.length === 1 ? 'memory' : 'memories'})`;
        }

        console.log('[updateFilterBadge] Showing FILTERED state');
    } else {
        // FULL GRAPH STATE - Show normal status with refresh button
        if (statusFull) statusFull.style.display = 'block';
        if (statusFiltered) statusFiltered.style.display = 'none';

        // Update count
        if (statusFullText && graphData && graphData.nodes) {
            const maxNodes = document.getElementById('graph-max-nodes')?.value || 50;
            statusFullText.textContent = `Showing ${graphData.nodes.length} of ${maxNodes} memories`;
        }

        console.log('[updateFilterBadge] Showing FULL state');
    }
}

// Transform D3 data format → Cytoscape format
function transformDataForCytoscape(data) {
    const elements = [];

    // Add nodes
    data.nodes.forEach(node => {
        const label = node.category || node.project_name || `Memory #${node.id}`;
        const contentPreview = node.content_preview || node.summary || node.content || '';
        const preview = contentPreview.substring(0, 50) + (contentPreview.length > 50 ? '...' : '');

        elements.push({
            group: 'nodes',
            data: {
                id: String(node.id),
                label: label,
                content: node.content || '',
                summary: node.summary || '',
                content_preview: preview,
                category: node.category || '',
                project_name: node.project_name || '',
                cluster_id: node.cluster_id || 0,
                importance: node.importance || 5,
                tags: node.tags || '',
                entities: node.entities || [],
                created_at: node.created_at || '',
                // For rendering
                weight: (node.importance || 5) * 5 // Size multiplier
            }
        });
    });

    // Add edges
    data.links.forEach(link => {
        const sourceId = String(typeof link.source === 'object' ? link.source.id : link.source);
        const targetId = String(typeof link.target === 'object' ? link.target.id : link.target);

        elements.push({
            group: 'edges',
            data: {
                id: `${sourceId}-${targetId}`,
                source: sourceId,
                target: targetId,
                weight: link.weight || 0.5,
                relationship_type: link.relationship_type || '',
                shared_entities: link.shared_entities || []
            }
        });
    });

    return elements;
}

// Render graph with Cytoscape.js
function renderGraph(data) {
    const container = document.getElementById('graph-container');
    if (!container) {
        console.error('Graph container not found');
        return;
    }

    // Clear existing graph
    if (cy) {
        cy.destroy();
    }

    // Check node count for performance tier
    const nodeCount = data.nodes.length;
    let layout = determineBestLayout(nodeCount);

    // Transform data
    const elements = transformDataForCytoscape(data);

    if (elements.length === 0) {
        const emptyMsg = document.createElement('div');
        emptyMsg.style.cssText = 'text-align:center; padding:50px; color:#666;';
        emptyMsg.textContent = 'No memories found. Try adjusting filters.';
        container.textContent = ''; // Clear safely
        container.appendChild(emptyMsg);
        return;
    }

    // Clear container (remove spinner/old content) - safe approach
    container.textContent = '';
    console.log('[renderGraph] Container cleared, initializing Cytoscape with', elements.length, 'elements');

    // Initialize Cytoscape WITHOUT running layout yet
    try {
        cy = cytoscape({
            container: container,
            elements: elements,
            style: getCytoscapeStyles(),
            layout: { name: 'preset' }, // Don't run layout yet
            minZoom: 0.2,
            maxZoom: 3,
            wheelSensitivity: 0.05,  // Reduced from 0.2 - less sensitive zoom
            autoungrabify: false,
            autounselectify: false,
            // Mobile touch support
            touchTapThreshold: 8,  // Pixels of movement allowed for tap (vs drag)
            desktopTapThreshold: 4,  // Desktop click threshold
            pixelRatio: 'auto'  // Retina/HiDPI support
        });
        console.log('[renderGraph] Cytoscape initialized successfully, nodes:', cy.nodes().length);
    } catch (error) {
        console.error('[renderGraph] Cytoscape initialization failed:', error);
        showError('Failed to render graph: ' + error.message);
        return;
    }

    // Add interactions
    addCytoscapeInteractions();

    // Add navigator (mini-map) if available
    if (cy.navigator && nodeCount > 50) {
        cy.navigator({
            container: false, // Will be added to DOM separately if needed
            viewLiveFramerate: 0,
            dblClickDelay: 200,
            removeCustomContainer: false,
            rerenderDelay: 100
        });
    }

    // Update UI
    updateFilterBadge();
    updateGraphStats(data);

    // Announce graph load to screen readers
    updateScreenReaderStatus(`Graph loaded with ${data.nodes.length} memories and ${data.links.length} connections`);

    // Check if we should restore saved layout or run fresh layout
    const hasSavedLayout = localStorage.getItem('slm_graph_layout');

    if (hasSavedLayout) {
        // Restore saved positions, then fit
        restoreSavedLayout();
        console.log('[renderGraph] Restored saved layout positions');
        cy.fit(null, 80);
    } else {
        // No saved layout - run layout algorithm with fit
        console.log('[renderGraph] Running fresh layout:', layout);
        const layoutConfig = getLayoutConfig(layout);
        const graphLayout = cy.layout(layoutConfig);

        // CRITICAL: Wait for layout to finish, THEN force fit
        graphLayout.on('layoutstop', function() {
            console.log('[renderGraph] Layout completed, forcing fit to viewport');
            cy.fit(null, 80); // Force center with 80px padding
        });

        graphLayout.run();
    }
}

// Determine best layout based on node count (3-tier strategy)
function determineBestLayout(nodeCount) {
    if (nodeCount <= 500) {
        return 'fcose'; // Full interactive graph
    } else if (nodeCount <= 2000) {
        return 'cose'; // Faster force-directed
    } else {
        return 'circle'; // Focus mode (circular for large graphs)
    }
}

// Get layout configuration
function getLayoutConfig(layoutName) {
    const configs = {
        'fcose': {
            name: 'fcose',
            quality: 'default',
            randomize: false,
            animate: false,  // Disabled for stability
            fit: true,
            padding: 80,  // Increased padding to keep within bounds
            nodeSeparation: 100,
            idealEdgeLength: 100,
            edgeElasticity: 0.45,
            nestingFactor: 0.1,
            gravity: 0.25,
            numIter: 2500,
            tile: true,
            tilingPaddingVertical: 10,
            tilingPaddingHorizontal: 10,
            gravityRangeCompound: 1.5,
            gravityCompound: 1.0,
            gravityRange: 3.8
        },
        'cose': {
            name: 'cose',
            animate: false,  // Disabled for stability
            fit: true,
            padding: 80,  // Increased padding
            nodeRepulsion: 8000,
            idealEdgeLength: 100,
            edgeElasticity: 100,
            nestingFactor: 5,
            gravity: 80,
            numIter: 1000,
            randomize: false
        },
        'circle': {
            name: 'circle',
            animate: true,
            animationDuration: 1000,
            fit: true,
            padding: 50,
            sort: function(a, b) {
                return b.data('importance') - a.data('importance');
            }
        },
        'grid': {
            name: 'grid',
            animate: true,
            animationDuration: 1000,
            fit: true,
            padding: 50,
            sort: function(a, b) {
                return b.data('importance') - a.data('importance');
            }
        },
        'breadthfirst': {
            name: 'breadthfirst',
            animate: true,
            animationDuration: 1000,
            fit: true,
            padding: 50,
            directed: false,
            circle: false,
            spacingFactor: 1.5,
            sort: function(a, b) {
                return b.data('importance') - a.data('importance');
            }
        },
        'concentric': {
            name: 'concentric',
            animate: true,
            animationDuration: 1000,
            fit: true,
            padding: 50,
            concentric: function(node) {
                return node.data('importance');
            },
            levelWidth: function() {
                return 2;
            }
        }
    };

    return configs[layoutName] || configs['fcose'];
}

// Cytoscape.js styles
function getCytoscapeStyles() {
    return [
        {
            selector: 'node',
            style: {
                'background-color': function(ele) {
                    return getClusterColor(ele.data('cluster_id'));
                },
                'width': function(ele) {
                    return Math.max(20, ele.data('weight'));
                },
                'height': function(ele) {
                    return Math.max(20, ele.data('weight'));
                },
                'label': 'data(label)',
                'font-size': '10px',
                'text-valign': 'center',
                'text-halign': 'center',
                'color': '#333',
                'text-outline-width': 2,
                'text-outline-color': '#fff',
                'border-width': function(ele) {
                    // Trust score → border thickness (if available)
                    return 2;
                },
                'border-color': '#555'
            }
        },
        {
            selector: 'node:selected',
            style: {
                'border-width': 4,
                'border-color': '#667eea',
                'background-color': '#667eea'
            }
        },
        {
            selector: 'node.highlighted',
            style: {
                'border-width': 4,
                'border-color': '#ff6b6b',
                'box-shadow': '0 0 20px #ff6b6b'
            }
        },
        {
            selector: 'node.dimmed',
            style: {
                'opacity': 0.3
            }
        },
        {
            selector: 'node.keyboard-focused',
            style: {
                'border-width': 5,
                'border-color': '#0066ff',
                'border-style': 'solid',
                'box-shadow': '0 0 15px #0066ff'
            }
        },
        {
            selector: 'edge',
            style: {
                'width': function(ele) {
                    return Math.max(1, ele.data('weight') * 3);
                },
                'line-color': '#ccc',
                'line-style': function(ele) {
                    return ele.data('weight') > 0.3 ? 'solid' : 'dashed';
                },
                'curve-style': 'bezier',
                'target-arrow-shape': 'none',
                'opacity': 0.6
            }
        },
        {
            selector: 'edge.highlighted',
            style: {
                'line-color': '#667eea',
                'width': 3,
                'opacity': 1
            }
        },
        {
            selector: 'edge.dimmed',
            style: {
                'opacity': 0.1
            }
        }
    ];
}

// Add all interactions (hover, click, double-click, drag)
function addCytoscapeInteractions() {
    if (!cy) return;

    // Hover: Show tooltip
    cy.on('mouseover', 'node', function(evt) {
        const node = evt.target;
        const pos = evt.renderedPosition;
        showTooltip(node, pos.x, pos.y);

        // Highlight connected nodes
        node.addClass('highlighted');
        node.connectedEdges().addClass('highlighted');
        node.neighborhood('node').addClass('highlighted');

        // Dim others
        cy.nodes().not(node).not(node.neighborhood('node')).addClass('dimmed');
        cy.edges().not(node.connectedEdges()).addClass('dimmed');
    });

    cy.on('mouseout', 'node', function(evt) {
        hideTooltip();

        // Remove highlighting
        cy.elements().removeClass('highlighted').removeClass('dimmed');
    });

    // Single click: Open modal preview
    cy.on('tap', 'node', function(evt) {
        const node = evt.target;
        openMemoryModal(node);
    });

    // Double click: Navigate to Memories tab
    cy.on('dbltap', 'node', function(evt) {
        const node = evt.target;
        navigateToMemoryTab(node.data('id'));
    });

    // Enable node dragging
    cy.on('drag', 'node', function(evt) {
        // Node position is automatically updated by Cytoscape
    });

    // Save layout when drag ends
    cy.on('dragfree', 'node', function(evt) {
        saveLayoutPositions();
    });

    // Pan & zoom events (for performance monitoring)
    let panZoomTimeout;
    cy.on('pan zoom', function() {
        clearTimeout(panZoomTimeout);
        panZoomTimeout = setTimeout(() => {
            saveLayoutPositions();
        }, 1000);
    });

    // Add keyboard navigation
    setupKeyboardNavigation();
}

// Tooltip (XSS-safe: uses textContent and createElement)
let tooltipTimeout;
function showTooltip(node, x, y) {
    clearTimeout(tooltipTimeout);
    tooltipTimeout = setTimeout(() => {
        let tooltip = document.getElementById('graph-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'graph-tooltip';
            tooltip.style.cssText = 'position:fixed; background:#333; color:#fff; padding:10px; border-radius:6px; font-size:12px; max-width:300px; z-index:10000; pointer-events:none; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';
            document.body.appendChild(tooltip);
        }

        // Build tooltip content safely (no innerHTML)
        tooltip.textContent = ''; // Clear
        const data = node.data();

        const title = document.createElement('strong');
        title.textContent = data.label;
        tooltip.appendChild(title);

        tooltip.appendChild(document.createElement('br'));

        const meta = document.createElement('span');
        meta.style.color = '#aaa';
        meta.textContent = `Cluster ${data.cluster_id} • Importance ${data.importance}`;
        tooltip.appendChild(meta);

        tooltip.appendChild(document.createElement('br'));

        const preview = document.createElement('span');
        preview.style.cssText = 'font-size:11px; color:#ccc;';
        preview.textContent = data.content_preview;
        tooltip.appendChild(preview);

        tooltip.style.display = 'block';
        tooltip.style.left = (x + 20) + 'px';
        tooltip.style.top = (y - 20) + 'px';
    }, 200);
}

function hideTooltip() {
    clearTimeout(tooltipTimeout);
    const tooltip = document.getElementById('graph-tooltip');
    if (tooltip) {
        tooltip.style.display = 'none';
    }
}

// Open modal preview (reuse existing modal.js function)
function openMemoryModal(node) {
    const memoryData = {
        id: node.data('id'),
        content: node.data('content'),
        summary: node.data('summary'),
        category: node.data('category'),
        project_name: node.data('project_name'),
        cluster_id: node.data('cluster_id'),
        importance: node.data('importance'),
        tags: node.data('tags'),
        created_at: node.data('created_at')
    };

    // Call existing openMemoryDetail function from modal.js
    if (typeof openMemoryDetail === 'function') {
        openMemoryDetail(memoryData);
    } else {
        console.error('openMemoryDetail function not found. Is modal.js loaded?');
    }
}

// Navigate to Memories tab and scroll to memory
function navigateToMemoryTab(memoryId) {
    // Switch to Memories tab
    const memoriesTab = document.querySelector('a[href="#memories"]');
    if (memoriesTab) {
        memoriesTab.click();
    }

    // Scroll to memory after a short delay (for tab to load)
    setTimeout(() => {
        if (typeof scrollToMemory === 'function') {
            scrollToMemory(memoryId);
        } else {
            console.warn('scrollToMemory function not found in memories.js');
        }
    }, 300);
}

// Save layout positions to localStorage
function saveLayoutPositions() {
    if (!cy) return;

    const positions = {};
    cy.nodes().forEach(node => {
        positions[node.id()] = node.position();
    });

    try {
        localStorage.setItem('slm_graph_layout', JSON.stringify(positions));
    } catch (e) {
        console.warn('Failed to save graph layout:', e);
    }
}

// Restore saved layout positions
function restoreSavedLayout() {
    if (!cy) return;

    try {
        const saved = localStorage.getItem('slm_graph_layout');
        if (saved) {
            const positions = JSON.parse(saved);
            cy.nodes().forEach(node => {
                const pos = positions[node.id()];
                if (pos) {
                    node.position(pos);
                }
            });
        }
    } catch (e) {
        console.warn('Failed to restore graph layout:', e);
    }
}

// Layout selector: Change graph layout
function changeGraphLayout(layoutName) {
    if (!cy) return;

    currentLayout = layoutName;
    const layout = cy.layout(getLayoutConfig(layoutName));
    layout.run();

    // Save preference
    localStorage.setItem('slm_graph_layout_preference', layoutName);
}

// Expand neighbors: Show only this node + connected nodes
function expandNeighbors(memoryId) {
    if (!cy) return;

    const node = cy.getElementById(String(memoryId));
    if (!node || node.length === 0) return;

    // Hide all nodes and edges
    cy.elements().addClass('dimmed');

    // Show target node + neighbors + connecting edges
    node.removeClass('dimmed');
    node.neighborhood().removeClass('dimmed');
    node.connectedEdges().removeClass('dimmed');

    // Fit view to visible elements
    cy.fit(node.neighborhood().union(node), 50);
}

// Update graph stats display
function updateGraphStats(data) {
    const statsEl = document.getElementById('graph-stats');
    if (statsEl) {
        // Clear and rebuild safely
        statsEl.textContent = '';

        const nodeBadge = document.createElement('span');
        nodeBadge.className = 'badge bg-primary';
        nodeBadge.textContent = `${data.nodes.length} nodes`;
        statsEl.appendChild(nodeBadge);

        const edgeBadge = document.createElement('span');
        edgeBadge.className = 'badge bg-secondary';
        edgeBadge.textContent = `${data.links.length} edges`;
        statsEl.appendChild(document.createTextNode(' '));
        statsEl.appendChild(edgeBadge);

        const clusterBadge = document.createElement('span');
        clusterBadge.className = 'badge bg-info';
        clusterBadge.textContent = `${data.clusters?.length || 0} clusters`;
        statsEl.appendChild(document.createTextNode(' '));
        statsEl.appendChild(clusterBadge);
    }
}

// Loading spinner helpers
function showLoadingSpinner() {
    const container = document.getElementById('graph-container');
    if (container) {
        container.textContent = ''; // Clear safely

        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'text-align:center; padding:100px;';

        const spinner = document.createElement('div');
        spinner.className = 'spinner-border text-primary';
        spinner.setAttribute('role', 'status');
        wrapper.appendChild(spinner);

        const text = document.createElement('p');
        text.style.marginTop = '20px';
        text.textContent = 'Loading graph...';
        wrapper.appendChild(text);

        container.appendChild(wrapper);
    }
}

function hideLoadingSpinner() {
    // Do nothing - renderGraph() already cleared the spinner
    // If we clear here, we destroy the Cytoscape canvas!
    console.log('[hideLoadingSpinner] Graph already rendered, spinner cleared by renderGraph()');
}

function showError(message) {
    const container = document.getElementById('graph-container');
    if (container) {
        container.textContent = ''; // Clear safely

        const alert = document.createElement('div');
        alert.className = 'alert alert-danger';
        alert.setAttribute('role', 'alert');
        alert.style.margin = '50px';
        alert.textContent = message;
        container.appendChild(alert);
    }
}

// Initialize on page load
function setupGraphEventListeners() {
    // Load graph when Graph tab is clicked
    const graphTab = document.querySelector('a[href="#graph"]');
    if (graphTab) {
        // CRITICAL FIX: Add click handler to clear filter even when already on KG tab
        // Bootstrap's shown.bs.tab only fires when SWITCHING TO tab, not when clicking same tab!
        graphTab.addEventListener('click', function(event) {
            console.log('[Event] Knowledge Graph tab CLICKED');

            // Check if we're viewing a filtered graph
            const hasFilter = filterState.cluster_id || filterState.entity;

            if (hasFilter && cy) {
                console.log('[Event] Click detected on KG tab while filter active - clearing filter');

                // Clear filter state
                filterState = { cluster_id: null, entity: null };

                // Clear URL completely
                const cleanUrl = window.location.origin + window.location.pathname;
                window.history.replaceState({}, '', cleanUrl);
                console.log('[Event] URL cleaned to:', cleanUrl);

                // CRITICAL: Clear saved layout positions so nodes don't stay in corner
                localStorage.removeItem('slm_graph_layout');
                console.log('[Event] Cleared saved layout positions');

                // Reload with full graph
                loadGraph();
            }
        });

        // Also keep shown.bs.tab for when switching FROM another tab TO KG tab
        graphTab.addEventListener('shown.bs.tab', function(event) {
            console.log('[Event] Knowledge Graph tab SHOWN (tab switch)');

            if (cy) {
                // Graph already exists - user is returning to KG tab from another tab
                // Clear filter and reload to show full graph
                console.log('[Event] Returning to KG tab from another tab - clearing filter');

                // Clear filter state
                filterState = { cluster_id: null, entity: null };

                // Clear URL completely
                const cleanUrl = window.location.origin + window.location.pathname;
                window.history.replaceState({}, '', cleanUrl);
                console.log('[Event] URL cleaned to:', cleanUrl);

                // CRITICAL: Clear saved layout positions so nodes don't stay in corner
                localStorage.removeItem('slm_graph_layout');
                console.log('[Event] Cleared saved layout positions');

                // Reload with full graph (respects dropdown settings)
                loadGraph();
            } else {
                // First load - check if cluster filter is in URL (from cluster badge click)
                const urlParams = new URLSearchParams(window.location.search);
                const clusterIdParam = urlParams.get('cluster_id');

                if (clusterIdParam) {
                    console.log('[Event] First load with cluster filter:', clusterIdParam);
                    // Load with filter (will be applied in loadGraph)
                } else {
                    console.log('[Event] First load, no filter');
                }

                loadGraph();
            }
        });
    }

    // Reload graph when dropdown settings change
    const maxNodesSelect = document.getElementById('graph-max-nodes');
    if (maxNodesSelect) {
        maxNodesSelect.addEventListener('change', function() {
            console.log('[Event] Max nodes changed to:', this.value);

            // Clear any active filter when user manually changes settings
            if (filterState.cluster_id || filterState.entity) {
                console.log('[Event] Clearing filter due to dropdown change');
                filterState = { cluster_id: null, entity: null };

                // Clear URL
                const cleanUrl = window.location.origin + window.location.pathname;
                window.history.replaceState({}, '', cleanUrl);
            }

            // Clear saved layout when changing node count (different # of nodes = different layout)
            localStorage.removeItem('slm_graph_layout');
            console.log('[Event] Cleared saved layout due to settings change');

            loadGraph();
        });
    }

    const minImportanceSelect = document.getElementById('graph-min-importance');
    if (minImportanceSelect) {
        minImportanceSelect.addEventListener('change', function() {
            console.log('[Event] Min importance changed to:', this.value);

            // Clear any active filter when user manually changes settings
            if (filterState.cluster_id || filterState.entity) {
                console.log('[Event] Clearing filter due to dropdown change');
                filterState = { cluster_id: null, entity: null };

                // Clear URL
                const cleanUrl = window.location.origin + window.location.pathname;
                window.history.replaceState({}, '', cleanUrl);
            }

            // Clear saved layout when changing importance (different nodes = different layout)
            localStorage.removeItem('slm_graph_layout');
            console.log('[Event] Cleared saved layout due to settings change');

            loadGraph();
        });
    }

    console.log('[Init] Graph event listeners setup complete');
}

// Keyboard navigation for graph
function setupKeyboardNavigation() {
    if (!cy) return;

    const container = document.getElementById('graph-container');
    if (!container) return;

    // Make container focusable
    container.setAttribute('tabindex', '0');

    // Focus handler - enable keyboard nav when container is focused
    container.addEventListener('focus', function() {
        keyboardNavigationEnabled = true;
        if (cy.nodes().length > 0) {
            focusNodeAtIndex(0);
        }
    });

    container.addEventListener('blur', function() {
        keyboardNavigationEnabled = false;
        cy.nodes().removeClass('keyboard-focused');
    });

    // Keyboard event handler
    container.addEventListener('keydown', function(e) {
        if (!keyboardNavigationEnabled || !cy) return;

        const nodes = cy.nodes();
        if (nodes.length === 0) return;

        const currentNode = nodes[focusedNodeIndex];

        switch(e.key) {
            case 'Tab':
                e.preventDefault();
                if (e.shiftKey) {
                    // Shift+Tab: previous node
                    focusedNodeIndex = (focusedNodeIndex - 1 + nodes.length) % nodes.length;
                } else {
                    // Tab: next node
                    focusedNodeIndex = (focusedNodeIndex + 1) % nodes.length;
                }
                focusNodeAtIndex(focusedNodeIndex);
                announceNode(nodes[focusedNodeIndex]);
                break;

            case 'Enter':
            case ' ':
                e.preventDefault();
                if (currentNode) {
                    lastFocusedElement = container;
                    openMemoryModal(currentNode);
                }
                break;

            case 'ArrowRight':
                e.preventDefault();
                moveToAdjacentNode('right', currentNode);
                break;

            case 'ArrowLeft':
                e.preventDefault();
                moveToAdjacentNode('left', currentNode);
                break;

            case 'ArrowDown':
                e.preventDefault();
                moveToAdjacentNode('down', currentNode);
                break;

            case 'ArrowUp':
                e.preventDefault();
                moveToAdjacentNode('up', currentNode);
                break;

            case 'Escape':
                e.preventDefault();
                if (filterState.cluster_id || filterState.entity) {
                    clearGraphFilters();
                    updateScreenReaderStatus('Filters cleared, showing all memories');
                } else {
                    container.blur();
                    keyboardNavigationEnabled = false;
                }
                break;

            case 'Home':
                e.preventDefault();
                focusedNodeIndex = 0;
                focusNodeAtIndex(0);
                announceNode(nodes[0]);
                break;

            case 'End':
                e.preventDefault();
                focusedNodeIndex = nodes.length - 1;
                focusNodeAtIndex(focusedNodeIndex);
                announceNode(nodes[focusedNodeIndex]);
                break;
        }
    });
}

// Focus a node at specific index
function focusNodeAtIndex(index) {
    if (!cy) return;

    const nodes = cy.nodes();
    if (index < 0 || index >= nodes.length) return;

    // Remove focus from all nodes
    cy.nodes().removeClass('keyboard-focused');

    // Add focus to target node
    const node = nodes[index];
    node.addClass('keyboard-focused');

    // Center node in viewport with smooth animation
    cy.animate({
        center: { eles: node },
        zoom: Math.max(cy.zoom(), 1.0),
        duration: 300,
        easing: 'ease-in-out'
    });
}

// Move focus to adjacent node based on direction
function moveToAdjacentNode(direction, currentNode) {
    if (!currentNode) return;

    const nodes = cy.nodes();
    const currentPos = currentNode.position();
    let bestNode = null;
    let bestScore = Infinity;

    // Find adjacent nodes based on direction
    nodes.forEach((node, index) => {
        if (node.id() === currentNode.id()) return;

        const pos = node.position();
        const dx = pos.x - currentPos.x;
        const dy = pos.y - currentPos.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        let isCorrectDirection = false;
        let directionScore = 0;

        switch(direction) {
            case 'right':
                isCorrectDirection = dx > 0;
                directionScore = dx;
                break;
            case 'left':
                isCorrectDirection = dx < 0;
                directionScore = -dx;
                break;
            case 'down':
                isCorrectDirection = dy > 0;
                directionScore = dy;
                break;
            case 'up':
                isCorrectDirection = dy < 0;
                directionScore = -dy;
                break;
        }

        // Combine distance with direction preference
        if (isCorrectDirection) {
            const score = distance - (directionScore * 0.5);
            if (score < bestScore) {
                bestScore = score;
                bestNode = node;
                focusedNodeIndex = index;
            }
        }
    });

    if (bestNode) {
        focusNodeAtIndex(focusedNodeIndex);
        announceNode(bestNode);
    }
}

// Announce node to screen reader
function announceNode(node) {
    if (!node) return;

    const data = node.data();
    const message = `Memory ${data.id}: ${data.label}, Cluster ${data.cluster_id}, Importance ${data.importance} out of 10`;
    updateScreenReaderStatus(message);
}

// Update screen reader status
function updateScreenReaderStatus(message) {
    let statusRegion = document.getElementById('graph-sr-status');
    if (!statusRegion) {
        statusRegion = document.createElement('div');
        statusRegion.id = 'graph-sr-status';
        statusRegion.setAttribute('role', 'status');
        statusRegion.setAttribute('aria-live', 'polite');
        statusRegion.setAttribute('aria-atomic', 'true');
        statusRegion.style.cssText = 'position:absolute; left:-10000px; width:1px; height:1px; overflow:hidden;';
        document.body.appendChild(statusRegion);
    }
    statusRegion.textContent = message;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupGraphEventListeners);
} else {
    setupGraphEventListeners();
}
