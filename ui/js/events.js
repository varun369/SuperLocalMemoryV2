// SuperLocalMemory V2 - Live Events (v2.5 — SSE Stream)
// Depends on: core.js
// Security: All DOM built with safe methods (createElement/textContent).

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
                appendEventToStream(JSON.parse(e.data));
            } catch (err) { /* keepalive comments */ }
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
                try { appendEventToStream(JSON.parse(e.data)); } catch (err) { /* ignore */ }
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

    if (_eventStreamItems.length === 0) container.textContent = '';

    _eventStreamItems.push(event);
    if (_eventStreamItems.length > _maxEventStreamItems) _eventStreamItems.shift();

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

    filtered.forEach(function(event) { appendEventToStream(event); });
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
