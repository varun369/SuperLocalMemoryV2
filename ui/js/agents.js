// SuperLocalMemory V2 - Connected Agents + Trust Overview (v2.5)
// Depends on: core.js
// Security: All DOM built with safe methods (createElement/textContent).

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

            var tdTrust = document.createElement('td');
            var trustScore = agent.trust_score != null ? agent.trust_score : 0.667;
            tdTrust.className = trustScore < 0.3 ? 'text-danger fw-bold'
                : trustScore < 0.5 ? 'text-warning fw-bold' : 'text-success fw-bold';
            tdTrust.textContent = trustScore.toFixed(2);
            tr.appendChild(tdTrust);

            var tdW = document.createElement('td');
            tdW.textContent = agent.memories_written || 0;
            tr.appendChild(tdW);

            var tdR = document.createElement('td');
            tdR.textContent = agent.memories_recalled || 0;
            tr.appendChild(tdR);

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

        var cardData = [
            { value: (stats.total_signals || 0).toLocaleString(), label: 'Total Signals Collected', cls: '' },
            { value: (stats.avg_trust_score || 0.667).toFixed(3), label: 'Average Trust Score', cls: '' },
            { value: stats.enforcement || 'disabled', label: 'Enforcement Status', cls: 'text-info' }
        ];

        cardData.forEach(function(c) {
            var col = document.createElement('div');
            col.className = 'col-md-4';
            var card = document.createElement('div');
            card.className = 'border rounded p-3 text-center';
            var val = document.createElement('div');
            val.className = 'fs-4 fw-bold ' + c.cls;
            val.textContent = c.value;
            card.appendChild(val);
            var lbl = document.createElement('small');
            lbl.className = 'text-muted';
            lbl.textContent = c.label;
            card.appendChild(lbl);
            col.appendChild(card);
            row.appendChild(col);
        });

        container.appendChild(row);

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
