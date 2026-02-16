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

    // Store last focused element (for keyboard nav return)
    if (!window.lastFocusedElement) {
        window.lastFocusedElement = document.activeElement;
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

    // Graph action buttons (v2.6.5)
    if (mem.cluster_id || mem.id) {
        body.appendChild(document.createElement('hr'));

        var actionsDiv = document.createElement('div');
        actionsDiv.className = 'memory-detail-graph-actions';
        actionsDiv.style.cssText = 'display:flex; gap:10px; flex-wrap:wrap;';

        // Button 1: View Full Memory (navigate to Memories tab)
        var viewBtn = document.createElement('button');
        viewBtn.className = 'btn btn-primary btn-sm';
        var viewIcon = document.createElement('i');
        viewIcon.className = 'bi bi-journal-text';
        viewBtn.appendChild(viewIcon);
        viewBtn.appendChild(document.createTextNode(' View Full Memory'));
        viewBtn.onclick = function() {
            modal.hide();
            if (typeof navigateToMemoryTab === 'function') {
                navigateToMemoryTab(mem.id);
            } else {
                // Fallback: just switch tab
                const memoriesTab = document.querySelector('a[href="#memories"]');
                if (memoriesTab) memoriesTab.click();
            }
        };
        actionsDiv.appendChild(viewBtn);

        // Button 2: Expand Neighbors (show connected nodes in graph)
        var expandBtn = document.createElement('button');
        expandBtn.className = 'btn btn-outline-secondary btn-sm';
        var expandIcon = document.createElement('i');
        expandIcon.className = 'bi bi-diagram-3';
        expandBtn.appendChild(expandIcon);
        expandBtn.appendChild(document.createTextNode(' Expand Neighbors'));
        expandBtn.onclick = function() {
            modal.hide();
            // Switch to Graph tab
            const graphTab = document.querySelector('a[href="#graph"]');
            if (graphTab) graphTab.click();
            // Expand neighbors after a delay
            setTimeout(function() {
                if (typeof expandNeighbors === 'function') {
                    expandNeighbors(mem.id);
                }
            }, 500);
        };
        actionsDiv.appendChild(expandBtn);

        // Button 3: Filter to Cluster (show only this cluster in graph)
        if (mem.cluster_id) {
            var filterBtn = document.createElement('button');
            filterBtn.className = 'btn btn-outline-info btn-sm';
            var filterIcon = document.createElement('i');
            filterIcon.className = 'bi bi-funnel';
            filterBtn.appendChild(filterIcon);
            filterBtn.appendChild(document.createTextNode(' Filter to Cluster ' + mem.cluster_id));
            filterBtn.onclick = function() {
                modal.hide();
                // Switch to Graph tab
                const graphTab = document.querySelector('a[href="#graph"]');
                if (graphTab) graphTab.click();
                // Apply cluster filter after a delay
                setTimeout(function() {
                    if (typeof filterState !== 'undefined' && typeof filterByCluster === 'function' && typeof renderGraph === 'function') {
                        filterState.cluster_id = mem.cluster_id;
                        const filtered = filterByCluster(originalGraphData, mem.cluster_id);
                        renderGraph(filtered);
                        // Update URL
                        const url = new URL(window.location);
                        url.searchParams.set('cluster_id', mem.cluster_id);
                        window.history.replaceState({}, '', url);
                    }
                }, 500);
            };
            actionsDiv.appendChild(filterBtn);
        }

        body.appendChild(actionsDiv);
    }

    // v2.7.4: Add feedback buttons to modal body
    if (typeof createFeedbackButtons === 'function' && mem && mem.id) {
        var feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'mt-3 pt-2 border-top';
        var feedbackLabel = document.createElement('small');
        feedbackLabel.className = 'text-muted d-block mb-1';
        feedbackLabel.textContent = 'Was this memory useful?';
        feedbackDiv.appendChild(feedbackLabel);
        feedbackDiv.appendChild(createFeedbackButtons(mem.id));
        body.appendChild(feedbackDiv);
    }

    var modalEl = document.getElementById('memoryDetailModal');
    var modal = new bootstrap.Modal(modalEl);

    // v2.7.4: Start dwell time tracking
    if (typeof startDwellTracking === 'function' && mem && mem.id) {
        startDwellTracking(mem.id);
    }

    // Focus first interactive element when modal opens
    modalEl.addEventListener('shown.bs.modal', function() {
        const firstButton = modalEl.querySelector('button, a[href]');
        if (firstButton) {
            firstButton.focus();
        }
    }, { once: true });

    // Return focus when modal closes + stop dwell tracking
    modalEl.addEventListener('hidden.bs.modal', function() {
        // v2.7.4: Stop dwell time tracking
        if (typeof stopDwellTracking === 'function') {
            stopDwellTracking();
        }
        if (window.lastFocusedElement && typeof window.lastFocusedElement.focus === 'function') {
            window.lastFocusedElement.focus();
            window.lastFocusedElement = null;
        }
    }, { once: true });

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
