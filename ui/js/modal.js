// SuperLocalMemory V2 - Memory Detail Modal + Copy/Export
// Depends on: core.js
//
// Security: All dynamic values escaped via escapeHtml(). Data from local DB only.
// nosemgrep: innerHTML-xss — all dynamic values escaped

var currentMemoryDetail = null;

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

    // Build detail using DOM nodes for safety
    body.textContent = '';

    var contentDiv = document.createElement('div');
    contentDiv.className = 'memory-detail-content';
    contentDiv.textContent = content;
    body.appendChild(contentDiv);

    body.appendChild(document.createElement('hr'));

    var dl = document.createElement('dl');
    dl.className = 'memory-detail-meta row';

    // Left column
    var col1 = document.createElement('div');
    col1.className = 'col-md-6';
    addDetailRow(col1, 'ID', String(mem.id || '-'));
    addDetailBadgeRow(col1, 'Category', mem.category || 'None', 'bg-primary');
    addDetailRow(col1, 'Project', mem.project_name || '-');
    addDetailTagsRow(col1, 'Tags', tags);
    dl.appendChild(col1);

    // Right column
    var col2 = document.createElement('div');
    col2.className = 'col-md-6';
    addDetailBadgeRow(col2, 'Importance', importance + '/10', 'bg-' + importanceClass);
    addDetailRow(col2, 'Cluster', String(mem.cluster_id || '-'));
    addDetailRow(col2, 'Created', formatDateFull(mem.created_at));
    if (mem.updated_at) addDetailRow(col2, 'Updated', formatDateFull(mem.updated_at));

    if (typeof mem.score === 'number') {
        var pct = Math.round(mem.score * 100);
        addDetailRow(col2, 'Relevance Score', pct + '%');
    }
    dl.appendChild(col2);

    body.appendChild(dl);

    var modal = new bootstrap.Modal(document.getElementById('memoryDetailModal'));
    modal.show();
}

function addDetailRow(parent, label, value) {
    var dt = document.createElement('dt');
    dt.textContent = label;
    parent.appendChild(dt);
    var dd = document.createElement('dd');
    dd.textContent = value;
    parent.appendChild(dd);
}

function addDetailBadgeRow(parent, label, value, badgeClass) {
    var dt = document.createElement('dt');
    dt.textContent = label;
    parent.appendChild(dt);
    var dd = document.createElement('dd');
    var badge = document.createElement('span');
    badge.className = 'badge ' + badgeClass;
    badge.textContent = value;
    dd.appendChild(badge);
    parent.appendChild(dd);
}

function addDetailTagsRow(parent, label, tags) {
    var dt = document.createElement('dt');
    dt.textContent = label;
    parent.appendChild(dt);
    var dd = document.createElement('dd');
    var tagList = typeof tags === 'string' ? tags.split(',') : (tags || []);
    if (tagList.length === 0 || (tagList.length === 1 && !tagList[0].trim())) {
        dd.className = 'text-muted';
        dd.textContent = 'None';
    } else {
        tagList.forEach(function(t) {
            var tag = t.trim();
            if (tag) {
                var badge = document.createElement('span');
                badge.className = 'badge bg-secondary me-1';
                badge.textContent = tag;
                dd.appendChild(badge);
            }
        });
    }
    parent.appendChild(dd);
}

function copyMemoryToClipboard() {
    if (!currentMemoryDetail) return;
    var text = currentMemoryDetail.content || currentMemoryDetail.summary || '';
    navigator.clipboard.writeText(text).then(function() {
        showToast('Copied to clipboard');
    }).catch(function() {
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
