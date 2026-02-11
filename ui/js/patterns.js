// SuperLocalMemory V2 - Patterns View (Layer 4)
// Depends on: core.js

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
