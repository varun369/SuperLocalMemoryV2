// Neural Glass — Health Monitor Tab
// Real-time process health, RSS budget, worker heartbeat (v3.4.3)
// API: /api/v3/health/processes — returns {processes: {name: {pid, status}}, memory_mb, healthy}

(function() {
  'use strict';

  var REFRESH_INTERVAL = 10000;
  var refreshTimer = null;

  window.loadHealthMonitor = function() {
    fetchHealth();
    clearInterval(refreshTimer);
    refreshTimer = setInterval(function() {
      var pane = document.getElementById('health-pane');
      if (pane && pane.classList.contains('active')) fetchHealth();
    }, REFRESH_INTERVAL);
  };

  function fetchHealth() {
    Promise.all([
      fetch('/api/v3/health/processes').then(function(r) { return r.json(); }).catch(function() { return null; }),
      fetch('/api/v3/consolidation/status').then(function(r) { return r.json(); }).catch(function() { return null; }),
      fetch('/api/stats').then(function(r) { return r.json(); }).catch(function() { return null; })
    ]).then(function(results) {
      var health = results[0];
      var consolidation = results[1];
      var stats = results[2];

      if (!health) {
        renderHealthOffline();
        return;
      }

      renderHealthOverview(health, consolidation, stats);
      renderProcessTable(health.processes || {});
      renderBudgetAndInfo(health, consolidation);
    });
  }

  function renderHealthOverview(health, consolidation, stats) {
    var el = document.getElementById('health-overview');
    if (!el) return;

    var isHealthy = health.healthy === true;
    var totalRss = health.memory_mb || 0;
    var budget = 4096; // configurable via health monitor
    var usagePct = budget > 0 ? Math.min(100, Math.round((totalRss / budget) * 100)) : 0;
    var barClass = usagePct > 80 ? 'ng-progress-fill-error' : usagePct > 60 ? 'ng-progress-fill-warning' : '';

    // Extract PID from processes
    var daemonPid = 'N/A';
    var procs = health.processes || {};
    if (procs.parent && procs.parent.pid) daemonPid = procs.parent.pid;
    else if (procs.mcp_server && procs.mcp_server.pid) daemonPid = procs.mcp_server.pid;

    // Process count
    var procCount = Object.keys(procs).length;

    // Consolidation info
    var lastConsolidation = 'Never';
    if (consolidation && consolidation.last_run) {
      lastConsolidation = timeAgo(consolidation.last_run);
    }

    // Stats info
    var factCount = stats ? (stats.total_memories || stats.fact_count || 0) : 0;

    el.innerHTML =
      '<div class="row g-3 mb-4">' +
        healthCard('Overall',
          statusDotHtml(isHealthy ? 'healthy' : 'degraded') + ' ' + (isHealthy ? 'Healthy' : 'Degraded'),
          'bi-heart-pulse') +
        healthCard('Daemon PID', daemonPid, 'bi-cpu') +
        healthCard('Memory', totalRss.toFixed(0) + ' MB', 'bi-memory') +
        healthCard('Processes', procCount + ' active', 'bi-diagram-2') +
      '</div>' +
      '<div class="ng-glass" style="padding:16px;margin-bottom:24px">' +
        '<div style="display:flex;justify-content:space-between;margin-bottom:8px">' +
          '<span style="font-size:0.8125rem;font-weight:590">Memory Budget</span>' +
          '<span style="font-size:0.8125rem;color:var(--ng-text-secondary)">' + totalRss.toFixed(0) + ' / ' + budget + ' MB (' + usagePct + '%)</span>' +
        '</div>' +
        '<div class="ng-progress-bar">' +
          '<div class="ng-progress-fill ' + barClass + '" style="width:' + usagePct + '%"></div>' +
        '</div>' +
      '</div>';
  }

  function renderProcessTable(processes) {
    var el = document.getElementById('health-processes');
    if (!el) return;

    var keys = Object.keys(processes);
    if (keys.length === 0) {
      el.innerHTML = '<div style="padding:24px;color:var(--ng-text-tertiary);text-align:center">No processes reported</div>';
      return;
    }

    var html = '<div class="table-responsive"><table class="table table-sm">' +
      '<thead><tr><th>Process</th><th>PID</th><th>Status</th><th>Details</th></tr></thead><tbody>';

    keys.forEach(function(name) {
      var p = processes[name];
      if (typeof p !== 'object') return;
      var st = p.status || 'unknown';
      var pid = p.pid || 'N/A';
      var details = [];
      if (p.rss_mb) details.push(p.rss_mb.toFixed(1) + ' MB');
      if (p.cpu_percent) details.push('CPU ' + p.cpu_percent.toFixed(1) + '%');
      if (p.request_count) details.push(p.request_count + ' reqs');
      if (p.model) details.push(p.model);
      if (p.workers) details.push(p.workers + ' workers');

      html += '<tr>' +
        '<td style="font-weight:510">' + escapeHtml(formatProcessName(name)) + '</td>' +
        '<td><code>' + pid + '</code></td>' +
        '<td>' + statusDotHtml(st) + ' ' + capitalize(st) + '</td>' +
        '<td style="color:var(--ng-text-secondary);font-size:0.8125rem">' + (details.join(' · ') || '—') + '</td>' +
      '</tr>';
    });

    html += '</tbody></table></div>';
    el.innerHTML = html;
  }

  function renderBudgetAndInfo(health, consolidation) {
    var el = document.getElementById('health-budget-rules');
    if (!el) return;

    var items = [
      { label: 'Total Memory', value: (health.memory_mb || 0).toFixed(0) + ' MB' },
      { label: 'Healthy', value: health.healthy ? 'Yes' : 'No' },
      { label: 'RSS Budget', value: '4,096 MB' },
      { label: 'Heartbeat', value: '30s interval' },
      { label: 'Worker Recycle', value: 'After 1,000 reqs' }
    ];

    if (consolidation) {
      items.push({ label: 'Last Consolidation', value: consolidation.last_run ? timeAgo(consolidation.last_run) : 'Never' });
      if (consolidation.last_result) {
        items.push({ label: 'Blocks Compiled', value: String(consolidation.last_result.blocks_compiled || 0) });
        items.push({ label: 'Graph Edges', value: formatNumber(consolidation.last_result.total_edges || 0) });
      }
      items.push({ label: 'Store Counter', value: String(consolidation.store_count_since_last || 0) });
    }

    var html = '<div style="font-size:0.8125rem">';
    items.forEach(function(item) {
      html += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--ng-border-subtle)">' +
        '<span style="color:var(--ng-text-secondary)">' + item.label + '</span>' +
        '<span style="font-weight:590">' + item.value + '</span>' +
      '</div>';
    });
    html += '</div>';
    el.innerHTML = html;
  }

  function renderHealthOffline() {
    var el = document.getElementById('health-overview');
    if (!el) return;
    el.innerHTML =
      '<div class="row g-3 mb-4">' +
        healthCard('Overall', statusDotHtml('dead') + ' Offline', 'bi-heart-pulse') +
        healthCard('Daemon PID', 'N/A', 'bi-cpu') +
        healthCard('Memory', '0 MB', 'bi-memory') +
        healthCard('Processes', '0', 'bi-diagram-2') +
      '</div>';
  }

  function healthCard(label, value, icon) {
    return '<div class="col-md-3 col-6">' +
      '<div class="ng-glass" style="padding:16px;text-align:center">' +
        '<i class="bi ' + icon + '" style="font-size:1.25rem;color:var(--ng-accent);display:block;margin-bottom:8px"></i>' +
        '<div class="ng-stat-value" style="font-size:1.5rem">' + value + '</div>' +
        '<div class="ng-stat-label">' + label + '</div>' +
      '</div>' +
    '</div>';
  }

  function statusDotHtml(st) {
    var c = 'var(--ng-text-quaternary)';
    if (st === 'healthy' || st === 'active' || st === 'running') c = 'var(--ng-status-success)';
    else if (st === 'degraded' || st === 'stale') c = 'var(--ng-status-warning)';
    else if (st === 'dead' || st === 'error' || st === 'critical') c = 'var(--ng-status-error)';
    return '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + c + ';box-shadow:0 0 6px ' + c + '"></span>';
  }

  function formatProcessName(name) {
    return name.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });
  }

  function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; }
  function escapeHtml(s) { var d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
  function formatNumber(n) { return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function timeAgo(iso) {
    if (!iso) return 'N/A';
    var d = (Date.now() - new Date(iso).getTime()) / 1000;
    if (d < 0) d = 0;
    if (d < 60) return Math.floor(d) + 's ago';
    if (d < 3600) return Math.floor(d / 60) + 'm ago';
    if (d < 86400) return Math.floor(d / 3600) + 'h ago';
    return Math.floor(d / 86400) + 'd ago';
  }

  document.addEventListener('visibilitychange', function() {
    if (document.hidden) clearInterval(refreshTimer);
  });
})();
