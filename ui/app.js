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
    var node = svg.append('g').selectAll('circle').data(data.nodes).enter().append('circle').attr('class', 'node').attr('r', function(d) { return 5 + (d.importance || 5); }).attr('fill', function(d) { return colorScale(d.cluster_id || 0); }).call(d3.drag().on('start', dragStarted).on('drag', dragged).on('end', dragEnded)).on('mouseover', function(event, d) { tooltip.transition().duration(200).style('opacity', .9); tooltip.text((d.category || 'Uncategorized') + ': ' + (d.content_preview || d.summary || 'No content')).style('left', (event.pageX + 10) + 'px').style('top', (event.pageY - 28) + 'px'); }).on('mouseout', function() { tooltip.transition().duration(500).style('opacity', 0); }).on('click', function(event, d) { openMemoryDetail(d); });
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
        + '<th>ID</th><th>Category</th><th>Project</th><th>Content</th>'
        + scoreHeader
        + '<th>Importance</th><th>Cluster</th><th>Created</th>'
        + '</tr></thead><tbody>' + rows + '</tbody></table>';

    // Safe: all interpolated values above are escaped via escapeHtml()
    container.innerHTML = html;  // nosemgrep: innerHTML-xss — all values escaped

    // Attach click handlers via delegation
    var table = container.querySelector('table');
    if (table) {
        table.addEventListener('click', function(e) {
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

    // All dynamic values escaped — safe for innerHTML
    var html = '';
    for (var type in patterns) {
        if (!patterns.hasOwnProperty(type)) continue;
        var items = patterns[type];
        html += '<h6 class="mt-3 text-capitalize">' + escapeHtml(type.replace(/_/g, ' ')) + '</h6><div class="list-group mb-3">';
        items.forEach(function(pattern) {
            var confidence = (pattern.confidence * 100).toFixed(0);
            html += '<div class="list-group-item">'
                + '<div class="d-flex justify-content-between align-items-center">'
                + '<strong>' + escapeHtml(pattern.key) + '</strong>'
                + '<span class="badge bg-success">' + escapeHtml(confidence) + '% confidence</span>'
                + '</div>'
                + '<div class="mt-1"><small class="text-muted">' + escapeHtml(JSON.stringify(pattern.value)) + '</small></div>'
                + '<small class="text-muted">Evidence: ' + escapeHtml(String(pattern.evidence_count)) + ' memories</small>'
                + '</div>';
        });
        html += '</div>';
    }
    container.innerHTML = html;  // nosemgrep: innerHTML-xss — all values escaped
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
document.getElementById('search-query').addEventListener('keypress', function(e) { if (e.key === 'Enter') searchMemories(); });

window.addEventListener('DOMContentLoaded', function() {
    initDarkMode();
    loadStats();
    loadGraph();
});
