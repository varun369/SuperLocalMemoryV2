// SuperLocalMemory V2 - Core Utilities
// Shared functions used by all other modules.
// Security: All dynamic text MUST pass through escapeHtml() before DOM insertion.
// Data originates from our own trusted local SQLite database (localhost only).

// ============================================================================
// Dark Mode
// ============================================================================

function initDarkMode() {
    var saved = localStorage.getItem('slm-theme');
    var theme;
    if (saved) {
        theme = saved;
    } else {
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
        var eased = 1 - Math.pow(1 - progress, 3);
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
// Safe HTML builder — tagged template for escaped interpolation
// ============================================================================

function safeHtml(templateParts) {
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
// Stats (loaded on startup)
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
// Application Init (DOMContentLoaded)
// ============================================================================

window.addEventListener('DOMContentLoaded', function() {
    initDarkMode();
    loadProfiles();
    loadStats();
    loadGraph();

    // v2.5 — Event Bus + Agent Registry (graceful if functions don't exist)
    if (typeof initEventStream === 'function') initEventStream();
    if (typeof loadEventStats === 'function') loadEventStats();
    if (typeof loadAgents === 'function') loadAgents();
});
