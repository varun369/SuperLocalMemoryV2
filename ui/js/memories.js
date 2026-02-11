// SuperLocalMemory V2 - Memories List + Sorting
// Depends on: core.js, modal.js (openMemoryDetail)
//
// Security: All dynamic values are escaped via escapeHtml() before DOM insertion.
// The innerHTML usage in renderMemoriesTable is safe because every interpolated
// value passes through escapeHtml(). Data comes from our own local SQLite DB only.
// nosemgrep: innerHTML-xss — all dynamic values escaped via escapeHtml()

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
        lastSearchResults = null;
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

    window._slmMemories = memories;
    var scoreHeader = showScores ? '<th>Score</th>' : '';

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

    var tableHtml = '<table class="table table-hover memory-table"><thead><tr>'
        + '<th class="sortable" data-sort="id">ID</th>'
        + '<th class="sortable" data-sort="category">Category</th>'
        + '<th class="sortable" data-sort="project">Project</th>'
        + '<th>Content</th>'
        + scoreHeader
        + '<th class="sortable" data-sort="importance">Importance</th>'
        + '<th>Cluster</th>'
        + '<th class="sortable" data-sort="created">Created</th>'
        + '</tr></thead><tbody>' + rows + '</tbody></table>';

    // All values above escaped via escapeHtml() — safe for trusted local data
    container.textContent = '';
    container.insertAdjacentHTML('beforeend', tableHtml);

    var table = container.querySelector('table');
    if (table) {
        table.addEventListener('click', function(e) {
            var th = e.target.closest('th.sortable');
            if (th) { handleSort(th); return; }
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

    document.querySelectorAll('#memories-list th.sortable').forEach(function(h) {
        h.classList.remove('sort-asc', 'sort-desc');
    });
    th.classList.add('sort-' + currentSort.direction);

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
