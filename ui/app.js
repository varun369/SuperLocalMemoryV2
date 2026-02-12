// SuperLocalMemory V2 - UI Application
// Note: All data from API is from our own trusted local database.
// All user-facing strings are escaped via escapeHtml() before DOM insertion.
// innerHTML usage is safe here: all dynamic values are sanitized, and no
// external/untrusted input reaches the DOM.

let graphData = { nodes: [], links: [] };
let currentMemoryDetail = null;   // Memory currently shown in modal
let lastSearchResults = null;     // Cached search results for export

// ============================================================================
// Dark Mode
// ============================================================================

function initDarkMode() {
    var saved = localStorage.getItem('slm-theme');
    var theme;
    if (saved) {
        theme = saved;
    } else {
        // Respect system preference on first load
        theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    applyTheme(theme);
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    var icon = document.getElementById('theme-icon');
    if (icon) {
        icon.className = theme === 'dark' ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
    }
}

function toggleDarkMode() {
    var current = document.documentElement.getAttribute('data-bs-theme');
    var next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('slm-theme', next);
    applyTheme(next);
}

// ============================================================================
// Animated Counter
// ============================================================================

function animateCounter(elementId, target) {
    var el = document.getElementById(elementId);
    if (!el) return;
    var duration = 600;
    var startTime = null;

    function step(timestamp) {
        if (!startTime) startTime = timestamp;
        var progress = Math.min((timestamp - startTime) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        el.textContent = Math.floor(eased * target).toLocaleString();
        if (progress < 1) {
            requestAnimationFrame(step);
        } else {
            el.textContent = target.toLocaleString();
        }
    }

    if (target === 0) {
        el.textContent = '0';
    } else {
        requestAnimationFrame(step);
    }
}

// ============================================================================
// HTML Escaping — all dynamic text MUST pass through this before DOM insertion
// ============================================================================

function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(String(text)));
    return div.innerHTML;
}

// ============================================================================
// Loading / Empty State helpers
// ============================================================================

function showLoading(containerId, message) {
    var el = document.getElementById(containerId);
    if (!el) return;
    // Build DOM nodes instead of innerHTML for loading state
    el.textContent = '';
    var wrapper = document.createElement('div');
    wrapper.className = 'loading';
    var spinner = document.createElement('div');
    spinner.className = 'spinner-border text-primary';
    spinner.setAttribute('role', 'status');
    var msg = document.createElement('div');
    msg.textContent = message || 'Loading...';
    wrapper.appendChild(spinner);
    wrapper.appendChild(msg);
    el.appendChild(wrapper);
}

function showEmpty(containerId, icon, message) {
    var el = document.getElementById(containerId);
    if (!el) return;
    el.textContent = '';
    var wrapper = document.createElement('div');
    wrapper.className = 'empty-state';
    var iconEl = document.createElement('i');
    iconEl.className = 'bi bi-' + icon + ' d-block';
    var p = document.createElement('p');
    p.textContent = message;
    wrapper.appendChild(iconEl);
    wrapper.appendChild(p);
    el.appendChild(wrapper);
}

// ============================================================================
// Safe HTML builder — constructs sanitized HTML strings from trusted templates
// and escaped dynamic values. Used for table/card rendering where DOM-node-by-
// node construction would be impractical for 50+ row tables.
// ============================================================================

function safeHtml(templateParts) {
    // Tagged template literal helper: safeHtml`<b>${userValue}</b>`
    // All interpolated values are auto-escaped.
    var args = Array.prototype.slice.call(arguments, 1);
    var result = '';
    for (var i = 0; i < templateParts.length; i++) {
        result += templateParts[i];
        if (i < args.length) {
            result += escapeHtml(String(args[i]));
        }
    }
    return result;
}

// ============================================================================
// Stats
// ============================================================================

async function loadStats() {
    try {
        var response = await fetch('/api/stats');
        var data = await response.json();
        animateCounter('stat-memories', data.overview.total_memories);
        animateCounter('stat-clusters', data.overview.total_clusters);
        animateCounter('stat-nodes', data.overview.graph_nodes);
        animateCounter('stat-edges', data.overview.graph_edges);
        populateFilters(data.categories, data.projects);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function populateFilters(categories, projects) {
    var categorySelect = document.getElementById('filter-category');
    var projectSelect = document.getElementById('filter-project');
    categories.forEach(function(cat) {
        if (cat.category) {
            var option = document.createElement('option');
            option.value = cat.category;
            option.textContent = cat.category + ' (' + cat.count + ')';
            categorySelect.appendChild(option);
        }
    });
    projects.forEach(function(proj) {
        if (proj.project_name) {
            var option = document.createElement('option');
            option.value = proj.project_name;
            option.textContent = proj.project_name + ' (' + proj.count + ')';
            projectSelect.appendChild(option);
        }
    });
}

// ============================================================================
// Graph
// ============================================================================

async function loadGraph() {
    var maxNodes = document.getElementById('graph-max-nodes').value;
    try {
        var response = await fetch('/api/graph?max_nodes=' + maxNodes);
        graphData = await response.json();
        renderGraph(graphData);
    } catch (error) {
        console.error('Error loading graph:', error);
    }
}

function renderGraph(data) {
    var container = document.getElementById('graph-container');
    container.textContent = '';
    var width = container.clientWidth || 1200;
    var height = 600;
    var svg = d3.select('#graph-container').append('svg').attr('width', width).attr('height', height);
    var tooltip = d3.select('body').append('div').attr('class', 'tooltip-custom').style('opacity', 0);
    var colorScale = d3.scaleOrdinal(d3.schemeCategory10);
    var simulation = d3.forceSimulation(data.nodes).force('link', d3.forceLink(data.links).id(function(d) { return d.id; }).distance(100)).force('charge', d3.forceManyBody().strength(-200)).force('center', d3.forceCenter(width / 2, height / 2)).force('collision', d3.forceCollide().radius(20));
    var link = svg.append('g').selectAll('line').data(data.links).enter().append('line').attr('class', 'link').attr('stroke-width', function(d) { return Math.sqrt(d.weight * 2); });
    var node = svg.append('g').selectAll('circle').data(data.nodes).enter().append('circle').attr('class', 'node').attr('r', function(d) { return 5 + (d.importance || 5); }).attr('fill', function(d) { return colorScale(d.cluster_id || 0); }).call(d3.drag().on('start', dragStarted).on('drag', dragged).on('end', dragEnded)).on('mouseover', function(event, d) { tooltip.transition().duration(200).style('opacity', .9); var label = d.category || d.project_name || 'Memory #' + d.id; tooltip.text(label + ': ' + (d.content_preview || d.summary || 'No content')).style('left', (event.pageX + 10) + 'px').style('top', (event.pageY - 28) + 'px'); }).on('mouseout', function() { tooltip.transition().duration(500).style('opacity', 0); }).on('click', function(event, d) { openMemoryDetail(d); });
    simulation.on('tick', function() { link.attr('x1', function(d) { return d.source.x; }).attr('y1', function(d) { return d.source.y; }).attr('x2', function(d) { return d.target.x; }).attr('y2', function(d) { return d.target.y; }); node.attr('cx', function(d) { return d.x; }).attr('cy', function(d) { return d.y; }); });
    function dragStarted(event, d) { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
    function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
    function dragEnded(event, d) { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }
}

// ============================================================================
// Memories
// ============================================================================

async function loadMemories() {
    var category = document.getElementById('filter-category').value;
    var project = document.getElementById('filter-project').value;
    var url = '/api/memories?limit=50';
    if (category) url += '&category=' + encodeURIComponent(category);
    if (project) url += '&project_name=' + encodeURIComponent(project);

    showLoading('memories-list', 'Loading memories...');
    try {
        var response = await fetch(url);
        var data = await response.json();
        lastSearchResults = null; // Clear search cache when browsing
        var exportBtn = document.getElementById('export-search-btn');
        if (exportBtn) exportBtn.style.display = 'none';
        renderMemoriesTable(data.memories, false);
    } catch (error) {
        console.error('Error loading memories:', error);
        showEmpty('memories-list', 'exclamation-triangle', 'Failed to load memories');
    }
}

function renderMemoriesTable(memories, showScores) {
    var container = document.getElementById('memories-list');
    if (!memories || memories.length === 0) {
        showEmpty('memories-list', 'journal-x', 'No memories found. Try a different search or filter.');
        return;
    }

    // Store memories for row-click access
    window._slmMemories = memories;

    var scoreHeader = showScores ? '<th>Score</th>' : '';

    // All dynamic values below are escaped via escapeHtml() — safe for innerHTML.
    var rows = '';
    memories.forEach(function(mem, idx) {
        var content = mem.summary || mem.content || '';
        var contentPreview = content.length > 100 ? content.substring(0, 100) + '...' : content;
        var importance = mem.importance || 5;
        var importanceClass = importance >= 8 ? 'success' : importance >= 5 ? 'warning' : 'secondary';

        var scoreCell = '';
        if (showScores) {
            var score = mem.score || 0;
            var pct = Math.round(score * 100);
            var barColor = pct >= 70 ? '#43e97b' : pct >= 40 ? '#f9c74f' : '#f94144';
            scoreCell = '<td><span class="score-label">' + escapeHtml(String(pct)) + '%</span>'
                + '<div class="score-bar-container"><div class="score-bar">'
                + '<div class="score-bar-fill" style="width:' + pct + '%;background:' + barColor + '"></div>'
                + '</div></div></td>';
        }

        rows += '<tr data-mem-idx="' + idx + '">'
            + '<td>' + escapeHtml(String(mem.id)) + '</td>'
            + '<td><span class="badge bg-primary">' + escapeHtml(mem.category || 'None') + '</span></td>'
            + '<td><small>' + escapeHtml(mem.project_name || '-') + '</small></td>'
            + '<td class="memory-content" title="' + escapeHtml(content) + '">' + escapeHtml(contentPreview) + '</td>'
            + scoreCell
            + '<td><span class="badge bg-' + importanceClass + ' badge-importance">' + escapeHtml(String(importance)) + '</span></td>'
            + '<td>' + escapeHtml(String(mem.cluster_id || '-')) + '</td>'
            + '<td><small>' + escapeHtml(formatDate(mem.created_at)) + '</small></td>'
            + '</tr>';
    });

    var html = '<table class="table table-hover memory-table"><thead><tr>'
        + '<th class="sortable" data-sort="id">ID</th>'
        + '<th class="sortable" data-sort="category">Category</th>'
        + '<th class="sortable" data-sort="project">Project</th>'
        + '<th>Content</th>'
        + scoreHeader
        + '<th class="sortable" data-sort="importance">Importance</th>'
        + '<th>Cluster</th>'
        + '<th class="sortable" data-sort="created">Created</th>'
        + '</tr></thead><tbody>' + rows + '</tbody></table>';

    // Safe: all interpolated values above are escaped via escapeHtml()
    container.innerHTML = html;  // nosemgrep: innerHTML-xss — all values escaped

    // Attach click handlers via delegation
    var table = container.querySelector('table');
    if (table) {
        table.addEventListener('click', function(e) {
            // Check if clicking a sortable header
            var th = e.target.closest('th.sortable');
            if (th) {
                handleSort(th);
                return;
            }
            var row = e.target.closest('tr[data-mem-idx]');
            if (row) {
                var idx = parseInt(row.getAttribute('data-mem-idx'), 10);
                if (window._slmMemories && window._slmMemories[idx]) {
                    openMemoryDetail(window._slmMemories[idx]);
                }
            }
        });
    }
}

// ============================================================================
// Search
// ============================================================================

async function searchMemories() {
    var query = document.getElementById('search-query').value;
    if (!query.trim()) { loadMemories(); return; }

    showLoading('memories-list', 'Searching...');
    try {
        var response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, limit: 20, min_score: 0.3 })
        });
        var data = await response.json();

        // Sort by relevance score descending
        var results = data.results || [];
        results.sort(function(a, b) { return (b.score || 0) - (a.score || 0); });

        // Cache for export
        lastSearchResults = results;

        // Show export search results button
        var exportBtn = document.getElementById('export-search-btn');
        if (exportBtn) exportBtn.style.display = results.length > 0 ? '' : 'none';

        renderMemoriesTable(results, true);
    } catch (error) {
        console.error('Error searching:', error);
        showEmpty('memories-list', 'exclamation-triangle', 'Search failed. Please try again.');
    }
}

// ============================================================================
// Memory Detail Modal
// ============================================================================

function openMemoryDetail(mem) {
    currentMemoryDetail = mem;
    var body = document.getElementById('memory-detail-body');
    if (!mem) {
        body.textContent = 'No memory data';
        return;
    }

    var content = mem.content || mem.summary || '(no content)';
    var tags = mem.tags || '';
    var importance = mem.importance || 5;
    var importanceClass = importance >= 8 ? 'success' : importance >= 5 ? 'warning' : 'secondary';

    var scoreBlock = '';
    if (typeof mem.score === 'number') {
        var pct = Math.round(mem.score * 100);
        var barColor = pct >= 70 ? '#43e97b' : pct >= 40 ? '#f9c74f' : '#f94144';
        scoreBlock = '<dt>Relevance Score</dt><dd><span class="score-label">'
            + escapeHtml(String(pct)) + '%</span>'
            + '<div class="score-bar-container"><div class="score-bar">'
            + '<div class="score-bar-fill" style="width:' + pct + '%;background:' + barColor + '"></div>'
            + '</div></div></dd>';
    }

    // All values escaped — safe for innerHTML
    var html = '<div class="memory-detail-content">' + escapeHtml(content) + '</div>'
        + '<hr>'
        + '<dl class="memory-detail-meta row">'
        + '<div class="col-md-6">'
        + '<dt>ID</dt><dd>' + escapeHtml(String(mem.id || '-')) + '</dd>'
        + '<dt>Category</dt><dd><span class="badge bg-primary">' + escapeHtml(mem.category || 'None') + '</span></dd>'
        + '<dt>Project</dt><dd>' + escapeHtml(mem.project_name || '-') + '</dd>'
        + '<dt>Tags</dt><dd>' + (tags ? formatTags(tags) : '<span class="text-muted">None</span>') + '</dd>'
        + '</div>'
        + '<div class="col-md-6">'
        + '<dt>Importance</dt><dd><span class="badge bg-' + importanceClass + '">' + escapeHtml(String(importance)) + '/10</span></dd>'
        + '<dt>Cluster</dt><dd>' + escapeHtml(String(mem.cluster_id || '-')) + '</dd>'
        + '<dt>Created</dt><dd>' + escapeHtml(formatDateFull(mem.created_at)) + '</dd>'
        + (mem.updated_at ? '<dt>Updated</dt><dd>' + escapeHtml(formatDateFull(mem.updated_at)) + '</dd>' : '')
        + scoreBlock
        + '</div>'
        + '</dl>';

    body.innerHTML = html;  // nosemgrep: innerHTML-xss — all values escaped

    var modal = new bootstrap.Modal(document.getElementById('memoryDetailModal'));
    modal.show();
}

function formatTags(tags) {
    if (!tags) return '';
    var tagList = typeof tags === 'string' ? tags.split(',') : tags;
    return tagList.map(function(t) {
        var tag = t.trim();
        return tag ? '<span class="badge bg-secondary me-1">' + escapeHtml(tag) + '</span>' : '';
    }).join('');
}

// ============================================================================
// Copy / Export from Modal
// ============================================================================

function copyMemoryToClipboard() {
    if (!currentMemoryDetail) return;
    var text = currentMemoryDetail.content || currentMemoryDetail.summary || '';
    navigator.clipboard.writeText(text).then(function() {
        showToast('Copied to clipboard');
    }).catch(function() {
        // Fallback for older browsers
        var ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('Copied to clipboard');
    });
}

function exportMemoryAsMarkdown() {
    if (!currentMemoryDetail) return;
    var mem = currentMemoryDetail;
    var md = '# Memory #' + (mem.id || 'unknown') + '\n\n';
    md += '**Category:** ' + (mem.category || 'None') + '  \n';
    md += '**Project:** ' + (mem.project_name || '-') + '  \n';
    md += '**Importance:** ' + (mem.importance || 5) + '/10  \n';
    md += '**Tags:** ' + (mem.tags || 'None') + '  \n';
    md += '**Created:** ' + (mem.created_at || '-') + '  \n';
    if (mem.cluster_id) md += '**Cluster:** ' + mem.cluster_id + '  \n';
    md += '\n---\n\n';
    md += mem.content || mem.summary || '(no content)';
    md += '\n\n---\n*Exported from SuperLocalMemory V2*\n';

    downloadFile('memory-' + (mem.id || 'export') + '.md', md, 'text/markdown');
}

// ============================================================================
// Export All / Search Results
// ============================================================================

function exportAll(format) {
    // Trigger browser download from the API endpoint
    var url = '/api/export?format=' + encodeURIComponent(format);
    var category = document.getElementById('filter-category').value;
    var project = document.getElementById('filter-project').value;
    if (category) url += '&category=' + encodeURIComponent(category);
    if (project) url += '&project_name=' + encodeURIComponent(project);
    window.location.href = url;
}

function exportSearchResults() {
    if (!lastSearchResults || lastSearchResults.length === 0) {
        showToast('No search results to export');
        return;
    }
    var content = JSON.stringify({
        exported_at: new Date().toISOString(),
        query: document.getElementById('search-query').value,
        total: lastSearchResults.length,
        results: lastSearchResults
    }, null, 2);
    downloadFile('search-results-' + Date.now() + '.json', content, 'application/json');
}

// ============================================================================
// File Download helper
// ============================================================================

function downloadFile(filename, content, mimeType) {
    var blob = new Blob([content], { type: mimeType });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================================================
// Toast notification
// ============================================================================

function showToast(message) {
    var toast = document.createElement('div');
    toast.style.cssText = 'position:fixed;bottom:24px;right:24px;background:#333;color:#fff;padding:10px 20px;border-radius:8px;font-size:0.9rem;z-index:9999;opacity:0;transition:opacity 0.3s;';
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(function() { toast.style.opacity = '1'; });
    setTimeout(function() {
        toast.style.opacity = '0';
        setTimeout(function() {
            if (toast.parentNode) document.body.removeChild(toast);
        }, 300);
    }, 2000);
}

// ============================================================================
// Clusters
// ============================================================================

async function loadClusters() {
    showLoading('clusters-list', 'Loading clusters...');
    try {
        var response = await fetch('/api/clusters');
        var data = await response.json();
        renderClusters(data.clusters);
    } catch (error) {
        console.error('Error loading clusters:', error);
        showEmpty('clusters-list', 'collection', 'Failed to load clusters');
    }
}

function renderClusters(clusters) {
    var container = document.getElementById('clusters-list');
    if (!clusters || clusters.length === 0) {
        showEmpty('clusters-list', 'collection', 'No clusters found. Run "slm build-graph" to generate clusters.');
        return;
    }
    var colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a'];

    // All dynamic values escaped — safe for innerHTML
    var html = '';
    clusters.forEach(function(cluster, idx) {
        var color = colors[idx % colors.length];
        html += '<div class="card cluster-card" style="border-color: ' + color + '">'
            + '<div class="card-body">'
            + '<h6 class="card-title">Cluster ' + escapeHtml(String(cluster.cluster_id))
            + ' <span class="badge bg-secondary float-end">' + escapeHtml(String(cluster.member_count)) + ' memories</span></h6>'
            + '<p class="mb-2"><strong>Avg Importance:</strong> ' + escapeHtml(parseFloat(cluster.avg_importance).toFixed(1)) + '</p>'
            + '<p class="mb-2"><strong>Categories:</strong> ' + escapeHtml(cluster.categories || 'None') + '</p>'
            + '<div><strong>Top Entities:</strong><br/>';
        if (cluster.top_entities && cluster.top_entities.length > 0) {
            cluster.top_entities.forEach(function(e) {
                html += '<span class="badge bg-info entity-badge">' + escapeHtml(e.entity) + ' (' + escapeHtml(String(e.count)) + ')</span> ';
            });
        } else {
            html += '<span class="text-muted">No entities</span>';
        }
        html += '</div></div></div>';
    });
    container.innerHTML = html;  // nosemgrep: innerHTML-xss — all values escaped
}

// ============================================================================
// Patterns
// ============================================================================

async function loadPatterns() {
    showLoading('patterns-list', 'Loading patterns...');
    try {
        var response = await fetch('/api/patterns');
        var data = await response.json();
        renderPatterns(data.patterns);
    } catch (error) {
        console.error('Error loading patterns:', error);
        showEmpty('patterns-list', 'puzzle', 'Failed to load patterns');
    }
}

function renderPatterns(patterns) {
    var container = document.getElementById('patterns-list');
    if (!patterns || Object.keys(patterns).length === 0) {
        showEmpty('patterns-list', 'puzzle', 'No patterns learned yet. Use SuperLocalMemory for a while to build patterns.');
        return;
    }

    var typeIcons = { preference: 'heart', style: 'palette', terminology: 'code-slash' };
    var typeLabels = { preference: 'Preferences', style: 'Coding Style', terminology: 'Terminology' };

    // Build using DOM for safety
    container.textContent = '';

    for (var type in patterns) {
        if (!patterns.hasOwnProperty(type)) continue;
        var items = patterns[type];

        var header = document.createElement('h6');
        header.className = 'mt-3 mb-2';
        var icon = document.createElement('i');
        icon.className = 'bi bi-' + (typeIcons[type] || 'puzzle') + ' me-1';
        header.appendChild(icon);
        header.appendChild(document.createTextNode(typeLabels[type] || type));
        var countBadge = document.createElement('span');
        countBadge.className = 'badge bg-secondary ms-2';
        countBadge.textContent = items.length;
        header.appendChild(countBadge);
        container.appendChild(header);

        var group = document.createElement('div');
        group.className = 'list-group mb-3';

        items.forEach(function(pattern) {
            var pct = Math.round(pattern.confidence * 100);
            var barColor = pct >= 60 ? '#43e97b' : pct >= 40 ? '#f9c74f' : '#6c757d';
            var badgeClass = pct >= 60 ? 'bg-success' : pct >= 40 ? 'bg-warning text-dark' : 'bg-secondary';

            var item = document.createElement('div');
            item.className = 'list-group-item';

            var topRow = document.createElement('div');
            topRow.className = 'd-flex justify-content-between align-items-center';
            var keyEl = document.createElement('strong');
            keyEl.textContent = pattern.key;
            var badge = document.createElement('span');
            badge.className = 'badge ' + badgeClass;
            badge.textContent = pct + '%';
            topRow.appendChild(keyEl);
            topRow.appendChild(badge);
            item.appendChild(topRow);

            // Confidence bar
            var barContainer = document.createElement('div');
            barContainer.className = 'confidence-bar';
            var barFill = document.createElement('div');
            barFill.className = 'confidence-fill';
            barFill.style.width = pct + '%';
            barFill.style.background = barColor;
            barContainer.appendChild(barFill);
            item.appendChild(barContainer);

            var valueEl = document.createElement('div');
            valueEl.className = 'mt-1';
            var valueSmall = document.createElement('small');
            valueSmall.className = 'text-muted';
            valueSmall.textContent = typeof pattern.value === 'string' ? pattern.value : JSON.stringify(pattern.value);
            valueEl.appendChild(valueSmall);
            item.appendChild(valueEl);

            var evidenceEl = document.createElement('small');
            evidenceEl.className = 'text-muted';
            evidenceEl.textContent = 'Evidence: ' + (pattern.evidence_count || '?') + ' memories';
            item.appendChild(evidenceEl);

            group.appendChild(item);
        });

        container.appendChild(group);
    }
}

// ============================================================================
// Timeline
// ============================================================================

async function loadTimeline() {
    showLoading('timeline-chart', 'Loading timeline...');
    try {
        var response = await fetch('/api/timeline?days=30');
        var data = await response.json();
        renderTimeline(data.timeline);
    } catch (error) {
        console.error('Error loading timeline:', error);
        showEmpty('timeline-chart', 'clock-history', 'Failed to load timeline');
    }
}

function renderTimeline(timeline) {
    var container = document.getElementById('timeline-chart');
    if (!timeline || timeline.length === 0) {
        showEmpty('timeline-chart', 'clock-history', 'No timeline data for the last 30 days.');
        return;
    }
    var margin = { top: 20, right: 20, bottom: 50, left: 50 };
    var width = container.clientWidth - margin.left - margin.right;
    var height = 300 - margin.top - margin.bottom;
    container.textContent = '';
    var svg = d3.select('#timeline-chart').append('svg').attr('width', width + margin.left + margin.right).attr('height', height + margin.top + margin.bottom).append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
    var x = d3.scaleBand().range([0, width]).domain(timeline.map(function(d) { return d.date || d.period; })).padding(0.1);
    var y = d3.scaleLinear().range([height, 0]).domain([0, d3.max(timeline, function(d) { return d.count; })]);
    svg.append('g').attr('transform', 'translate(0,' + height + ')').call(d3.axisBottom(x)).selectAll('text').attr('transform', 'rotate(-45)').style('text-anchor', 'end');
    svg.append('g').call(d3.axisLeft(y));
    svg.selectAll('.bar').data(timeline).enter().append('rect').attr('class', 'bar').attr('x', function(d) { return x(d.date || d.period); }).attr('y', function(d) { return y(d.count); }).attr('width', x.bandwidth()).attr('height', function(d) { return height - y(d.count); }).attr('fill', '#667eea').attr('rx', 3);
}

// ============================================================================
// Date Formatters
// ============================================================================

function formatDate(dateString) {
    if (!dateString) return '-';
    var date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatDateFull(dateString) {
    if (!dateString) return '-';
    var date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// ============================================================================
// Event Listeners
// ============================================================================

document.getElementById('memories-tab').addEventListener('shown.bs.tab', loadMemories);
document.getElementById('clusters-tab').addEventListener('shown.bs.tab', loadClusters);
document.getElementById('patterns-tab').addEventListener('shown.bs.tab', loadPatterns);
document.getElementById('timeline-tab').addEventListener('shown.bs.tab', loadTimeline);
document.getElementById('settings-tab').addEventListener('shown.bs.tab', loadSettings);
document.getElementById('search-query').addEventListener('keypress', function(e) { if (e.key === 'Enter') searchMemories(); });

document.getElementById('profile-select').addEventListener('change', function() {
    switchProfile(this.value);
});

document.getElementById('add-profile-btn').addEventListener('click', function() {
    createProfile();
});

var newProfileInput = document.getElementById('new-profile-name');
if (newProfileInput) {
    newProfileInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') createProfile();
    });
}

window.addEventListener('DOMContentLoaded', function() {
    initDarkMode();
    loadProfiles();
    loadStats();
    loadGraph();

    // v2.5 — Event Bus + Agent Registry
    initEventStream();
    loadEventStats();
    loadAgents();
});

// ============================================================================
// Profile Management
// ============================================================================

async function loadProfiles() {
    try {
        var response = await fetch('/api/profiles');
        var data = await response.json();
        var select = document.getElementById('profile-select');
        select.textContent = '';
        var profiles = data.profiles || [];
        var active = data.active_profile || 'default';

        profiles.forEach(function(p) {
            var opt = document.createElement('option');
            opt.value = p.name;
            opt.textContent = p.name + (p.memory_count ? ' (' + p.memory_count + ')' : '');
            if (p.name === active) opt.selected = true;
            select.appendChild(opt);
        });
    } catch (error) {
        console.error('Error loading profiles:', error);
    }
}

async function createProfile(nameOverride) {
    var name = nameOverride || document.getElementById('new-profile-name').value.trim();
    if (!name) {
        // Prompt with a simple browser dialog if called from the "+" button
        name = prompt('Enter new profile name:');
        if (!name || !name.trim()) return;
        name = name.trim();
    }

    // Validate: alphanumeric, dashes, underscores only
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
        showToast('Invalid name. Use letters, numbers, dashes, underscores.');
        return;
    }

    try {
        var response = await fetch('/api/profiles/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile_name: name })
        });
        var data = await response.json();
        if (response.status === 409) {
            showToast('Profile "' + name + '" already exists');
            return;
        }
        if (!response.ok) {
            showToast(data.detail || 'Failed to create profile');
            return;
        }
        showToast('Profile "' + name + '" created');
        var input = document.getElementById('new-profile-name');
        if (input) input.value = '';
        loadProfiles();
        loadProfilesTable();
    } catch (error) {
        console.error('Error creating profile:', error);
        showToast('Error creating profile');
    }
}

async function deleteProfile(name) {
    if (name === 'default') {
        showToast('Cannot delete the default profile');
        return;
    }
    if (!confirm('Delete profile "' + name + '"?\nIts memories will be moved to the default profile.')) {
        return;
    }
    try {
        var response = await fetch('/api/profiles/' + encodeURIComponent(name), {
            method: 'DELETE'
        });
        var data = await response.json();
        if (!response.ok) {
            showToast(data.detail || 'Failed to delete profile');
            return;
        }
        showToast(data.message || 'Profile deleted');
        loadProfiles();
        loadProfilesTable();
        loadStats();
    } catch (error) {
        console.error('Error deleting profile:', error);
        showToast('Error deleting profile');
    }
}

async function loadProfilesTable() {
    var container = document.getElementById('profiles-table');
    if (!container) return;
    try {
        var response = await fetch('/api/profiles');
        var data = await response.json();
        var profiles = data.profiles || [];
        var active = data.active_profile || 'default';

        if (profiles.length === 0) {
            showEmpty('profiles-table', 'people', 'No profiles found.');
            return;
        }

        var table = document.createElement('table');
        table.className = 'table table-sm mb-0';
        var thead = document.createElement('thead');
        var headRow = document.createElement('tr');
        ['Name', 'Memories', 'Status', 'Actions'].forEach(function(h) {
            var th = document.createElement('th');
            th.textContent = h;
            headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        table.appendChild(thead);

        var tbody = document.createElement('tbody');
        profiles.forEach(function(p) {
            var row = document.createElement('tr');

            var nameCell = document.createElement('td');
            var nameIcon = document.createElement('i');
            nameIcon.className = 'bi bi-person me-1';
            nameCell.appendChild(nameIcon);
            nameCell.appendChild(document.createTextNode(p.name));
            row.appendChild(nameCell);

            var countCell = document.createElement('td');
            countCell.textContent = (p.memory_count || 0) + ' memories';
            row.appendChild(countCell);

            var statusCell = document.createElement('td');
            if (p.name === active) {
                var badge = document.createElement('span');
                badge.className = 'badge bg-success';
                badge.textContent = 'Active';
                statusCell.appendChild(badge);
            } else {
                var switchBtn = document.createElement('button');
                switchBtn.className = 'btn btn-sm btn-outline-primary';
                switchBtn.textContent = 'Switch';
                switchBtn.addEventListener('click', (function(n) {
                    return function() { switchProfile(n); };
                })(p.name));
                statusCell.appendChild(switchBtn);
            }
            row.appendChild(statusCell);

            var actionsCell = document.createElement('td');
            if (p.name !== 'default') {
                var delBtn = document.createElement('button');
                delBtn.className = 'btn btn-sm btn-outline-danger btn-delete-profile';
                delBtn.title = 'Delete profile';
                var delIcon = document.createElement('i');
                delIcon.className = 'bi bi-trash';
                delBtn.appendChild(delIcon);
                delBtn.addEventListener('click', (function(n) {
                    return function() { deleteProfile(n); };
                })(p.name));
                actionsCell.appendChild(delBtn);
            } else {
                var protectedBadge = document.createElement('span');
                protectedBadge.className = 'badge bg-secondary';
                protectedBadge.textContent = 'Protected';
                actionsCell.appendChild(protectedBadge);
            }
            row.appendChild(actionsCell);

            tbody.appendChild(row);
        });
        table.appendChild(tbody);

        container.textContent = '';
        container.appendChild(table);
    } catch (error) {
        console.error('Error loading profiles table:', error);
        showEmpty('profiles-table', 'exclamation-triangle', 'Failed to load profiles');
    }
}

async function switchProfile(profileName) {
    try {
        var response = await fetch('/api/profiles/' + encodeURIComponent(profileName) + '/switch', {
            method: 'POST'
        });
        var data = await response.json();
        if (data.success || data.active_profile) {
            showToast('Switched to profile: ' + profileName);
            loadProfiles();
            loadStats();
            loadGraph();
            loadProfilesTable();
            var activeTab = document.querySelector('#mainTabs .nav-link.active');
            if (activeTab) activeTab.click();
        } else {
            showToast('Failed to switch profile');
        }
    } catch (error) {
        console.error('Error switching profile:', error);
        showToast('Error switching profile');
    }
}

// ============================================================================
// Settings & Backup
// ============================================================================

async function loadSettings() {
    loadProfilesTable();
    loadBackupStatus();
    loadBackupList();
}

async function loadBackupStatus() {
    try {
        var response = await fetch('/api/backup/status');
        var data = await response.json();
        renderBackupStatus(data);
        document.getElementById('backup-interval').value = data.interval_hours <= 24 ? '24' : '168';
        document.getElementById('backup-max').value = data.max_backups || 10;
        document.getElementById('backup-enabled').checked = data.enabled !== false;
    } catch (error) {
        var container = document.getElementById('backup-status');
        var alert = document.createElement('div');
        alert.className = 'alert alert-warning mb-0';
        alert.textContent = 'Auto-backup not available. Update to v2.4.0+.';
        container.textContent = '';
        container.appendChild(alert);
    }
}

function renderBackupStatus(data) {
    var container = document.getElementById('backup-status');
    container.textContent = '';

    var lastBackup = data.last_backup ? formatDateFull(data.last_backup) : 'Never';
    var nextBackup = data.next_backup || 'N/A';
    if (nextBackup === 'overdue') nextBackup = 'Overdue';
    else if (nextBackup !== 'N/A' && nextBackup !== 'unknown') nextBackup = formatDateFull(nextBackup);

    var statusColor = data.enabled ? 'text-success' : 'text-secondary';
    var statusText = data.enabled ? 'Active' : 'Disabled';

    // Build DOM nodes for safety
    var row = document.createElement('div');
    row.className = 'row g-2 mb-2';

    var stats = [
        { value: statusText, label: 'Status', cls: statusColor },
        { value: String(data.backup_count || 0), label: 'Backups', cls: '' },
        { value: (data.total_size_mb || 0) + ' MB', label: 'Storage', cls: '' }
    ];

    stats.forEach(function(s) {
        var col = document.createElement('div');
        col.className = 'col-4';
        var stat = document.createElement('div');
        stat.className = 'backup-stat';
        var val = document.createElement('div');
        val.className = 'value ' + s.cls;
        val.textContent = s.value;
        var lbl = document.createElement('div');
        lbl.className = 'label';
        lbl.textContent = s.label;
        stat.appendChild(val);
        stat.appendChild(lbl);
        col.appendChild(stat);
        row.appendChild(col);
    });
    container.appendChild(row);

    var details = [
        { label: 'Last backup:', value: lastBackup },
        { label: 'Next backup:', value: nextBackup },
        { label: 'Interval:', value: data.interval_display || '-' }
    ];
    details.forEach(function(d) {
        var div = document.createElement('div');
        div.className = 'small text-muted';
        var strong = document.createElement('strong');
        strong.textContent = d.label + ' ';
        div.appendChild(strong);
        div.appendChild(document.createTextNode(d.value));
        container.appendChild(div);
    });
}

async function saveBackupConfig() {
    try {
        var response = await fetch('/api/backup/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                interval_hours: parseInt(document.getElementById('backup-interval').value),
                max_backups: parseInt(document.getElementById('backup-max').value),
                enabled: document.getElementById('backup-enabled').checked
            })
        });
        var data = await response.json();
        renderBackupStatus(data);
        showToast('Backup settings saved');
    } catch (error) {
        console.error('Error saving backup config:', error);
        showToast('Failed to save backup settings');
    }
}

async function createBackupNow() {
    showToast('Creating backup...');
    try {
        var response = await fetch('/api/backup/create', { method: 'POST' });
        var data = await response.json();
        if (data.success) {
            showToast('Backup created: ' + data.filename);
            loadBackupStatus();
            loadBackupList();
        } else {
            showToast('Backup failed');
        }
    } catch (error) {
        console.error('Error creating backup:', error);
        showToast('Backup failed');
    }
}

async function loadBackupList() {
    try {
        var response = await fetch('/api/backup/list');
        var data = await response.json();
        renderBackupList(data.backups || []);
    } catch (error) {
        var container = document.getElementById('backup-list');
        container.textContent = 'Backup list unavailable';
    }
}

function renderBackupList(backups) {
    var container = document.getElementById('backup-list');
    if (!backups || backups.length === 0) {
        showEmpty('backup-list', 'archive', 'No backups yet. Create your first backup above.');
        return;
    }

    // Build table using DOM nodes
    var table = document.createElement('table');
    table.className = 'table table-sm';
    var thead = document.createElement('thead');
    var headRow = document.createElement('tr');
    ['Filename', 'Size', 'Age', 'Created'].forEach(function(h) {
        var th = document.createElement('th');
        th.textContent = h;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');
    backups.forEach(function(b) {
        var row = document.createElement('tr');
        var age = b.age_hours < 48 ? Math.round(b.age_hours) + 'h ago' : Math.round(b.age_hours / 24) + 'd ago';
        var cells = [b.filename, b.size_mb + ' MB', age, formatDateFull(b.created)];
        cells.forEach(function(text) {
            var td = document.createElement('td');
            td.textContent = text;
            row.appendChild(td);
        });
        tbody.appendChild(row);
    });
    table.appendChild(tbody);

    container.textContent = '';
    container.appendChild(table);
}

// ============================================================================
// Column Sorting
// ============================================================================

var currentSort = { column: null, direction: 'asc' };

function handleSort(th) {
    var col = th.getAttribute('data-sort');
    if (!col) return;

    if (currentSort.column === col) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = col;
        currentSort.direction = 'asc';
    }

    // Update header classes
    document.querySelectorAll('#memories-list th.sortable').forEach(function(h) {
        h.classList.remove('sort-asc', 'sort-desc');
    });
    th.classList.add('sort-' + currentSort.direction);

    // Sort the data
    if (!window._slmMemories) return;
    var memories = window._slmMemories.slice();
    var dir = currentSort.direction === 'asc' ? 1 : -1;

    memories.sort(function(a, b) {
        var av, bv;
        switch (col) {
            case 'id': return ((a.id || 0) - (b.id || 0)) * dir;
            case 'importance': return ((a.importance || 0) - (b.importance || 0)) * dir;
            case 'category':
                av = (a.category || '').toLowerCase(); bv = (b.category || '').toLowerCase();
                return av < bv ? -dir : av > bv ? dir : 0;
            case 'project':
                av = (a.project_name || '').toLowerCase(); bv = (b.project_name || '').toLowerCase();
                return av < bv ? -dir : av > bv ? dir : 0;
            case 'created':
                av = a.created_at || ''; bv = b.created_at || '';
                return av < bv ? -dir : av > bv ? dir : 0;
            case 'score': return ((a.score || 0) - (b.score || 0)) * dir;
            default: return 0;
        }
    });

    window._slmMemories = memories;
    var showScores = memories.length > 0 && typeof memories[0].score === 'number';
    renderMemoriesTable(memories, showScores);
}

// ============================================================================
// v2.5 — Live Event Stream (SSE)
// ============================================================================
// Security note: All dynamic values are escaped via escapeHtml() before DOM insertion.
// Data originates from our own trusted local SQLite database (localhost only).
// No external/untrusted user input reaches the DOM — same pattern as existing code above.

var _eventSource = null;
var _eventStreamItems = [];
var _maxEventStreamItems = 200;

function initEventStream() {
    try {
        _eventSource = new EventSource('/events/stream');

        _eventSource.onopen = function() {
            var badge = document.getElementById('event-connection-status');
            if (badge) {
                badge.textContent = 'Connected';
                badge.className = 'badge bg-success me-2';
            }
        };

        _eventSource.onmessage = function(e) {
            try {
                var event = JSON.parse(e.data);
                appendEventToStream(event);
            } catch (err) {
                // Ignore parse errors (keepalive comments)
            }
        };

        _eventSource.onerror = function() {
            var badge = document.getElementById('event-connection-status');
            if (badge) {
                badge.textContent = 'Reconnecting...';
                badge.className = 'badge bg-warning me-2';
            }
        };

        ['memory.created', 'memory.updated', 'memory.deleted', 'memory.recalled',
         'agent.connected', 'agent.disconnected', 'graph.updated', 'pattern.learned'
        ].forEach(function(type) {
            _eventSource.addEventListener(type, function(e) {
                try {
                    appendEventToStream(JSON.parse(e.data));
                } catch (err) { /* ignore */ }
            });
        });
    } catch (err) {
        console.log('SSE not available:', err);
        var badge = document.getElementById('event-connection-status');
        if (badge) {
            badge.textContent = 'Unavailable';
            badge.className = 'badge bg-secondary me-2';
        }
    }
}

function appendEventToStream(event) {
    var container = document.getElementById('event-stream');
    if (!container) return;

    if (_eventStreamItems.length === 0) {
        container.textContent = '';
    }

    _eventStreamItems.push(event);
    if (_eventStreamItems.length > _maxEventStreamItems) {
        _eventStreamItems.shift();
    }

    var filter = document.getElementById('event-type-filter');
    var filterValue = filter ? filter.value : '';
    if (filterValue && event.event_type !== filterValue) return;

    var typeColors = {
        'memory.created': 'text-success', 'memory.updated': 'text-info',
        'memory.deleted': 'text-danger', 'memory.recalled': 'text-primary',
        'agent.connected': 'text-warning', 'agent.disconnected': 'text-secondary',
        'graph.updated': 'text-info', 'pattern.learned': 'text-success'
    };
    var typeIcons = {
        'memory.created': 'bi-plus-circle', 'memory.updated': 'bi-pencil',
        'memory.deleted': 'bi-trash', 'memory.recalled': 'bi-search',
        'agent.connected': 'bi-plug', 'agent.disconnected': 'bi-plug',
        'graph.updated': 'bi-diagram-3', 'pattern.learned': 'bi-lightbulb'
    };

    var colorClass = typeColors[event.event_type] || 'text-muted';
    var iconClass = typeIcons[event.event_type] || 'bi-circle';
    var ts = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : '';
    var payload = event.payload || {};
    var preview = payload.content_preview || payload.agent_id || payload.agent_name || '';
    if (preview.length > 80) preview = preview.substring(0, 80) + '...';

    // Build event line using safe DOM methods + escapeHtml for all dynamic content
    var div = document.createElement('div');
    div.className = 'event-line mb-1 pb-1 border-bottom border-opacity-25';

    var timeSpan = document.createElement('small');
    timeSpan.className = 'text-muted';
    timeSpan.textContent = ts;

    var icon = document.createElement('i');
    icon.className = 'bi ' + iconClass + ' ' + colorClass;
    icon.style.marginLeft = '6px';

    var typeSpan = document.createElement('span');
    typeSpan.className = colorClass + ' fw-bold';
    typeSpan.style.marginLeft = '4px';
    typeSpan.textContent = event.event_type;

    div.appendChild(timeSpan);
    div.appendChild(document.createTextNode(' '));
    div.appendChild(icon);
    div.appendChild(document.createTextNode(' '));
    div.appendChild(typeSpan);
    div.appendChild(document.createTextNode(' '));

    if (event.memory_id) {
        var badge = document.createElement('span');
        badge.className = 'badge bg-secondary';
        badge.textContent = '#' + event.memory_id;
        div.appendChild(badge);
        div.appendChild(document.createTextNode(' '));
    }

    var previewSpan = document.createElement('span');
    previewSpan.className = 'text-muted';
    previewSpan.textContent = preview;
    div.appendChild(previewSpan);

    container.insertBefore(div, container.firstChild);

    while (container.children.length > _maxEventStreamItems) {
        container.removeChild(container.lastChild);
    }
}

function filterEvents() {
    var container = document.getElementById('event-stream');
    if (!container) return;
    container.textContent = '';

    var filter = document.getElementById('event-type-filter');
    var filterValue = filter ? filter.value : '';

    var filtered = filterValue
        ? _eventStreamItems.filter(function(e) { return e.event_type === filterValue; })
        : _eventStreamItems;

    filtered.forEach(function(event) {
        appendEventToStream(event);
    });
}

function clearEventStream() {
    _eventStreamItems = [];
    var container = document.getElementById('event-stream');
    if (container) {
        container.textContent = '';
        var placeholder = document.createElement('div');
        placeholder.className = 'text-muted text-center py-4';
        var pIcon = document.createElement('i');
        pIcon.className = 'bi bi-broadcast';
        pIcon.style.fontSize = '2rem';
        placeholder.appendChild(pIcon);
        var pText = document.createElement('p');
        pText.className = 'mt-2';
        pText.textContent = 'Event stream cleared. Waiting for new events...';
        placeholder.appendChild(pText);
        container.appendChild(placeholder);
    }
}

async function loadEventStats() {
    try {
        var response = await fetch('/api/events/stats');
        var stats = await response.json();
        var el;
        el = document.getElementById('event-stat-total');
        if (el) el.textContent = (stats.total_events || 0).toLocaleString();
        el = document.getElementById('event-stat-24h');
        if (el) el.textContent = (stats.events_last_24h || 0).toLocaleString();
        el = document.getElementById('event-stat-listeners');
        if (el) el.textContent = (stats.listener_count || 0).toLocaleString();
        el = document.getElementById('event-stat-buffer');
        if (el) el.textContent = (stats.buffer_size || 0).toLocaleString();
    } catch (err) {
        console.log('Event stats not available:', err);
    }
}

// ============================================================================
// v2.5 — Connected Agents
// ============================================================================

async function loadAgents() {
    try {
        var response = await fetch('/api/agents');
        var data = await response.json();
        var agents = data.agents || [];
        var stats = data.stats || {};

        var el;
        el = document.getElementById('agent-stat-total');
        if (el) el.textContent = (stats.total_agents || 0).toLocaleString();
        el = document.getElementById('agent-stat-active');
        if (el) el.textContent = (stats.active_last_24h || 0).toLocaleString();
        el = document.getElementById('agent-stat-writes');
        if (el) el.textContent = (stats.total_writes || 0).toLocaleString();
        el = document.getElementById('agent-stat-recalls');
        if (el) el.textContent = (stats.total_recalls || 0).toLocaleString();

        var container = document.getElementById('agents-list');
        if (!container) return;

        if (agents.length === 0) {
            container.textContent = '';
            var empty = document.createElement('div');
            empty.className = 'text-muted text-center py-4';
            var emptyIcon = document.createElement('i');
            emptyIcon.className = 'bi bi-robot';
            emptyIcon.style.fontSize = '2rem';
            empty.appendChild(emptyIcon);
            var emptyText = document.createElement('p');
            emptyText.className = 'mt-2';
            emptyText.textContent = 'No agents registered yet. Agents appear automatically when they connect via MCP, CLI, or REST.';
            empty.appendChild(emptyText);
            container.appendChild(empty);
            loadTrustOverview();
            return;
        }

        // Build agent table using safe DOM methods
        var table = document.createElement('table');
        table.className = 'table table-hover table-sm';
        var thead = document.createElement('thead');
        var headerRow = document.createElement('tr');
        ['Agent', 'Protocol', 'Trust', 'Writes', 'Recalls', 'Last Seen'].forEach(function(h) {
            var th = document.createElement('th');
            th.textContent = h;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        var tbody = document.createElement('tbody');
        agents.forEach(function(agent) {
            var tr = document.createElement('tr');

            // Agent name cell
            var tdName = document.createElement('td');
            var strong = document.createElement('strong');
            strong.textContent = agent.agent_name || agent.agent_id;
            tdName.appendChild(strong);
            tdName.appendChild(document.createElement('br'));
            var smallId = document.createElement('small');
            smallId.className = 'text-muted';
            smallId.textContent = agent.agent_id;
            tdName.appendChild(smallId);
            tr.appendChild(tdName);

            // Protocol badge
            var tdProto = document.createElement('td');
            var protoBadge = document.createElement('span');
            var protocolColors = {
                'mcp': 'bg-primary', 'cli': 'bg-success', 'rest': 'bg-info',
                'python': 'bg-secondary', 'a2a': 'bg-warning'
            };
            protoBadge.className = 'badge ' + (protocolColors[agent.protocol] || 'bg-secondary');
            protoBadge.textContent = agent.protocol;
            tdProto.appendChild(protoBadge);
            tr.appendChild(tdProto);

            // Trust score
            var tdTrust = document.createElement('td');
            var trustScore = agent.trust_score != null ? agent.trust_score : 1.0;
            tdTrust.className = trustScore < 0.7 ? 'text-danger fw-bold'
                : trustScore < 0.9 ? 'text-warning fw-bold' : 'text-success fw-bold';
            tdTrust.textContent = trustScore.toFixed(2);
            tr.appendChild(tdTrust);

            // Writes
            var tdW = document.createElement('td');
            tdW.textContent = agent.memories_written || 0;
            tr.appendChild(tdW);

            // Recalls
            var tdR = document.createElement('td');
            tdR.textContent = agent.memories_recalled || 0;
            tr.appendChild(tdR);

            // Last seen
            var tdLast = document.createElement('td');
            var lastSmall = document.createElement('small');
            lastSmall.textContent = agent.last_seen ? new Date(agent.last_seen).toLocaleString() : 'Never';
            tdLast.appendChild(lastSmall);
            tr.appendChild(tdLast);

            tbody.appendChild(tr);
        });
        table.appendChild(tbody);

        container.textContent = '';
        container.appendChild(table);

        loadTrustOverview();

    } catch (err) {
        console.log('Agents not available:', err);
        var container = document.getElementById('agents-list');
        if (container) {
            container.textContent = '';
            var msg = document.createElement('small');
            msg.className = 'text-muted';
            msg.textContent = 'Agent registry not available. This feature requires v2.5+.';
            container.appendChild(msg);
        }
    }
}

async function loadTrustOverview() {
    try {
        var response = await fetch('/api/trust/stats');
        var stats = await response.json();
        var container = document.getElementById('trust-overview');
        if (!container) return;

        container.textContent = '';
        var row = document.createElement('div');
        row.className = 'row g-3';

        // Total signals card
        var col1 = document.createElement('div');
        col1.className = 'col-md-4';
        var card1 = document.createElement('div');
        card1.className = 'border rounded p-3 text-center';
        var val1 = document.createElement('div');
        val1.className = 'fs-4 fw-bold';
        val1.textContent = (stats.total_signals || 0).toLocaleString();
        card1.appendChild(val1);
        var lbl1 = document.createElement('small');
        lbl1.className = 'text-muted';
        lbl1.textContent = 'Total Signals Collected';
        card1.appendChild(lbl1);
        col1.appendChild(card1);
        row.appendChild(col1);

        // Avg trust card
        var col2 = document.createElement('div');
        col2.className = 'col-md-4';
        var card2 = document.createElement('div');
        card2.className = 'border rounded p-3 text-center';
        var val2 = document.createElement('div');
        val2.className = 'fs-4 fw-bold';
        val2.textContent = (stats.avg_trust_score || 1.0).toFixed(3);
        card2.appendChild(val2);
        var lbl2 = document.createElement('small');
        lbl2.className = 'text-muted';
        lbl2.textContent = 'Average Trust Score';
        card2.appendChild(lbl2);
        col2.appendChild(card2);
        row.appendChild(col2);

        // Enforcement card
        var col3 = document.createElement('div');
        col3.className = 'col-md-4';
        var card3 = document.createElement('div');
        card3.className = 'border rounded p-3 text-center';
        var val3 = document.createElement('div');
        val3.className = 'fs-4 fw-bold text-info';
        val3.textContent = stats.enforcement || 'disabled';
        card3.appendChild(val3);
        var lbl3 = document.createElement('small');
        lbl3.className = 'text-muted';
        lbl3.textContent = 'Enforcement Status';
        card3.appendChild(lbl3);
        col3.appendChild(card3);
        row.appendChild(col3);

        container.appendChild(row);

        // Signal breakdown
        if (stats.by_signal_type && Object.keys(stats.by_signal_type).length > 0) {
            var breakdownDiv = document.createElement('div');
            breakdownDiv.className = 'col-12 mt-3';
            var h6 = document.createElement('h6');
            h6.textContent = 'Signal Breakdown';
            breakdownDiv.appendChild(h6);
            var badgeWrap = document.createElement('div');
            badgeWrap.className = 'd-flex flex-wrap gap-2';
            Object.keys(stats.by_signal_type).forEach(function(type) {
                var count = stats.by_signal_type[type];
                var signalClass = (type.indexOf('high_volume') >= 0 || type.indexOf('quick_delete') >= 0)
                    ? 'bg-danger' : (type.indexOf('recalled') >= 0 || type.indexOf('high_importance') >= 0)
                    ? 'bg-success' : 'bg-secondary';
                var b = document.createElement('span');
                b.className = 'badge ' + signalClass;
                b.textContent = type + ': ' + count;
                badgeWrap.appendChild(b);
            });
            breakdownDiv.appendChild(badgeWrap);
            container.appendChild(breakdownDiv);
        }

    } catch (err) {
        console.log('Trust stats not available:', err);
        var container = document.getElementById('trust-overview');
        if (container) {
            container.textContent = '';
            var msg = document.createElement('small');
            msg.className = 'text-muted';
            msg.textContent = 'Trust scoring data will appear here once agents interact with memory.';
            container.appendChild(msg);
        }
    }
}
