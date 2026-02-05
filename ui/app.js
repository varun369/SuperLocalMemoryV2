// SuperLocalMemory V2 - UI Application
// Note: All data from API is from our own trusted database

let graphData = { nodes: [], links: [] };

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        document.getElementById('stat-memories').textContent = data.overview.total_memories.toLocaleString();
        document.getElementById('stat-clusters').textContent = data.overview.total_clusters.toLocaleString();
        document.getElementById('stat-nodes').textContent = data.overview.graph_nodes.toLocaleString();
        document.getElementById('stat-edges').textContent = data.overview.graph_edges.toLocaleString();
        populateFilters(data.categories, data.projects);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function populateFilters(categories, projects) {
    const categorySelect = document.getElementById('filter-category');
    const projectSelect = document.getElementById('filter-project');
    categories.forEach(cat => {
        if (cat.category) {
            const option = document.createElement('option');
            option.value = cat.category;
            option.textContent = cat.category + ' (' + cat.count + ')';
            categorySelect.appendChild(option);
        }
    });
    projects.forEach(proj => {
        if (proj.project_name) {
            const option = document.createElement('option');
            option.value = proj.project_name;
            option.textContent = proj.project_name + ' (' + proj.count + ')';
            projectSelect.appendChild(option);
        }
    });
}

async function loadGraph() {
    const maxNodes = document.getElementById('graph-max-nodes').value;
    try {
        const response = await fetch('/api/graph?max_nodes=' + maxNodes);
        graphData = await response.json();
        renderGraph(graphData);
    } catch (error) {
        console.error('Error loading graph:', error);
    }
}

function renderGraph(data) {
    const container = document.getElementById('graph-container');
    container.textContent = '';
    const width = container.clientWidth || 1200;
    const height = 600;
    const svg = d3.select('#graph-container').append('svg').attr('width', width).attr('height', height);
    const tooltip = d3.select('body').append('div').attr('class', 'tooltip-custom').style('opacity', 0);
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10);
    const simulation = d3.forceSimulation(data.nodes).force('link', d3.forceLink(data.links).id(d => d.id).distance(100)).force('charge', d3.forceManyBody().strength(-200)).force('center', d3.forceCenter(width / 2, height / 2)).force('collision', d3.forceCollide().radius(20));
    const link = svg.append('g').selectAll('line').data(data.links).enter().append('line').attr('class', 'link').attr('stroke-width', d => Math.sqrt(d.weight * 2));
    const node = svg.append('g').selectAll('circle').data(data.nodes).enter().append('circle').attr('class', 'node').attr('r', d => 5 + (d.importance || 5)).attr('fill', d => colorScale(d.cluster_id || 0)).call(d3.drag().on('start', dragStarted).on('drag', dragged).on('end', dragEnded)).on('mouseover', function(event, d) { tooltip.transition().duration(200).style('opacity', .9); tooltip.text((d.category || 'Uncategorized') + ': ' + (d.content_preview || d.summary || 'No content')).style('left', (event.pageX + 10) + 'px').style('top', (event.pageY - 28) + 'px'); }).on('mouseout', function() { tooltip.transition().duration(500).style('opacity', 0); });
    simulation.on('tick', () => { link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y); node.attr('cx', d => d.x).attr('cy', d => d.y); });
    function dragStarted(event, d) { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
    function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
    function dragEnded(event, d) { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }
}

async function loadMemories() {
    const category = document.getElementById('filter-category').value;
    const project = document.getElementById('filter-project').value;
    let url = '/api/memories?limit=50';
    if (category) url += '&category=' + encodeURIComponent(category);
    if (project) url += '&project_name=' + encodeURIComponent(project);
    try {
        const response = await fetch(url);
        const data = await response.json();
        renderMemoriesTable(data.memories);
    } catch (error) { console.error('Error loading memories:', error); }
}

function renderMemoriesTable(memories) {
    const container = document.getElementById('memories-list');
    if (memories.length === 0) { container.textContent = 'No memories found'; return; }
    let html = '<table class="table table-hover memory-table"><thead><tr><th>ID</th><th>Category</th><th>Project</th><th>Content</th><th>Importance</th><th>Cluster</th><th>Created</th></tr></thead><tbody>';
    memories.forEach(mem => {
        const content = mem.summary || mem.content || '';
        const contentPreview = content.length > 80 ? content.substring(0, 80) + '...' : content;
        const importance = mem.importance || 5;
        const importanceClass = importance >= 8 ? 'success' : importance >= 5 ? 'warning' : 'secondary';
        html += '<tr><td>' + mem.id + '</td><td><span class="badge bg-primary">' + (mem.category || 'None') + '</span></td><td><small>' + (mem.project_name || '-') + '</small></td><td class="memory-content" title="' + content + '">' + contentPreview + '</td><td><span class="badge bg-' + importanceClass + ' badge-importance">' + importance + '</span></td><td>' + (mem.cluster_id || '-') + '</td><td><small>' + formatDate(mem.created_at) + '</small></td></tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

async function searchMemories() {
    const query = document.getElementById('search-query').value;
    if (!query.trim()) { loadMemories(); return; }
    try {
        const response = await fetch('/api/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, limit: 20, min_score: 0.3 }) });
        const data = await response.json();
        renderMemoriesTable(data.results);
    } catch (error) { console.error('Error searching:', error); }
}

async function loadClusters() {
    try {
        const response = await fetch('/api/clusters');
        const data = await response.json();
        renderClusters(data.clusters);
    } catch (error) { console.error('Error loading clusters:', error); }
}

function renderClusters(clusters) {
    const container = document.getElementById('clusters-list');
    if (clusters.length === 0) { container.textContent = 'No clusters found'; return; }
    const colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a'];
    let html = '';
    clusters.forEach((cluster, idx) => {
        const color = colors[idx % colors.length];
        html += '<div class="card cluster-card" style="border-color: ' + color + '"><div class="card-body"><h6 class="card-title">Cluster ' + cluster.cluster_id + ' <span class="badge bg-secondary float-end">' + cluster.member_count + ' memories</span></h6><p class="mb-2"><strong>Avg Importance:</strong> ' + parseFloat(cluster.avg_importance).toFixed(1) + '</p><p class="mb-2"><strong>Categories:</strong> ' + (cluster.categories || 'None') + '</p><div><strong>Top Entities:</strong><br/>';
        cluster.top_entities.forEach(e => { html += '<span class="badge bg-info entity-badge">' + e.entity + ' (' + e.count + ')</span> '; });
        html += '</div></div></div>';
    });
    container.innerHTML = html;
}

async function loadPatterns() {
    try {
        const response = await fetch('/api/patterns');
        const data = await response.json();
        renderPatterns(data.patterns);
    } catch (error) { console.error('Error loading patterns:', error); }
}

function renderPatterns(patterns) {
    const container = document.getElementById('patterns-list');
    if (Object.keys(patterns).length === 0) { container.textContent = 'No patterns learned yet'; return; }
    let html = '';
    for (const [type, items] of Object.entries(patterns)) {
        html += '<h6 class="mt-3 text-capitalize">' + type.replace('_', ' ') + '</h6><div class="list-group mb-3">';
        items.forEach(pattern => {
            const confidence = (pattern.confidence * 100).toFixed(0);
            html += '<div class="list-group-item"><div class="d-flex justify-content-between align-items-center"><strong>' + pattern.key + '</strong><span class="badge bg-success">' + confidence + '% confidence</span></div><div class="mt-1"><small class="text-muted">' + JSON.stringify(pattern.value) + '</small></div><small class="text-muted">Evidence: ' + pattern.evidence_count + ' memories</small></div>';
        });
        html += '</div>';
    }
    container.innerHTML = html;
}

async function loadTimeline() {
    try {
        const response = await fetch('/api/timeline?days=30');
        const data = await response.json();
        renderTimeline(data.timeline);
    } catch (error) { console.error('Error loading timeline:', error); }
}

function renderTimeline(timeline) {
    const container = document.getElementById('timeline-chart');
    if (timeline.length === 0) { container.textContent = 'No timeline data'; return; }
    const margin = { top: 20, right: 20, bottom: 50, left: 50 };
    const width = container.clientWidth - margin.left - margin.right;
    const height = 300 - margin.top - margin.bottom;
    container.textContent = '';
    const svg = d3.select('#timeline-chart').append('svg').attr('width', width + margin.left + margin.right).attr('height', height + margin.top + margin.bottom).append('g').attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
    const x = d3.scaleBand().range([0, width]).domain(timeline.map(d => d.date)).padding(0.1);
    const y = d3.scaleLinear().range([height, 0]).domain([0, d3.max(timeline, d => d.count)]);
    svg.append('g').attr('transform', 'translate(0,' + height + ')').call(d3.axisBottom(x)).selectAll('text').attr('transform', 'rotate(-45)').style('text-anchor', 'end');
    svg.append('g').call(d3.axisLeft(y));
    svg.selectAll('.bar').data(timeline).enter().append('rect').attr('class', 'bar').attr('x', d => x(d.date)).attr('y', d => y(d.count)).attr('width', x.bandwidth()).attr('height', d => height - y(d.count)).attr('fill', '#667eea');
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

document.getElementById('memories-tab').addEventListener('shown.bs.tab', loadMemories);
document.getElementById('clusters-tab').addEventListener('shown.bs.tab', loadClusters);
document.getElementById('patterns-tab').addEventListener('shown.bs.tab', loadPatterns);
document.getElementById('timeline-tab').addEventListener('shown.bs.tab', loadTimeline);
document.getElementById('search-query').addEventListener('keypress', function(e) { if (e.key === 'Enter') searchMemories(); });
window.addEventListener('DOMContentLoaded', () => { loadStats(); loadGraph(); });
