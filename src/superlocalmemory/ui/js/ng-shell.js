// Neural Glass Shell — Dashboard V2 "Neural Glass"
// Injects sidebar, restructures DOM, handles navigation
// Progressive enhancement: if this fails, Bootstrap tabs still work

(function() {
  'use strict';

  // ── Sidebar Navigation Config ──────────────────────────────
  var NAV_SECTIONS = [
    {
      label: 'Memory',
      items: [
        { id: 'dashboard-pane', icon: 'bi-speedometer2', text: 'Dashboard' },
        { id: 'graph-pane', icon: 'bi-diagram-3', text: 'Knowledge Graph' },
        { id: 'memories-pane', icon: 'bi-list-ul', text: 'Memories' },
        { id: 'recall-lab-pane', icon: 'bi-search-heart', text: 'Recall Lab' },
        { id: 'timeline-pane', icon: 'bi-clock-history', text: 'Timeline' }
      ]
    },
    {
      label: 'Intelligence',
      items: [
        { id: 'clusters-pane', icon: 'bi-collection', text: 'Clusters' },
        { id: 'patterns-pane', icon: 'bi-puzzle', text: 'Patterns' },
        { id: 'learning-pane', icon: 'bi-mortarboard', text: 'Learning' },
        { id: 'behavioral-pane', icon: 'bi-lightbulb', text: 'Behavioral' }
      ]
    },
    {
      label: 'System',
      items: [
        { id: 'events-pane', icon: 'bi-broadcast', text: 'Live Events' },
        { id: 'agents-pane', icon: 'bi-robot', text: 'Agents' },
        { id: 'trust-pane', icon: 'bi-shield-check', text: 'Trust' },
        { id: 'lifecycle-pane', icon: 'bi-hourglass-split', text: 'Lifecycle' },
        { id: 'compliance-pane', icon: 'bi-shield-lock', text: 'Compliance' },
        { id: 'math-health-pane', icon: 'bi-calculator', text: 'Math Health' },
        { id: 'ide-pane', icon: 'bi-plug', text: 'IDEs' }
      ]
    },
    {
      label: 'v3.4.3',
      items: [
        { id: 'health-pane', icon: 'bi-heart-pulse', text: 'Health Monitor', badge: 'NEW' },
        { id: 'ingestion-pane', icon: 'bi-cloud-download', text: 'Ingestion', badge: 'NEW' },
        { id: 'entities-pane', icon: 'bi-person-badge', text: 'Entity Explorer', badge: 'NEW' },
        { id: 'mesh-pane', icon: 'bi-share', text: 'Mesh Peers', badge: 'NEW' }
      ]
    },
    {
      label: 'Config',
      items: [
        { id: 'settings-pane', icon: 'bi-gear', text: 'Settings' }
      ]
    }
  ];

  // ── Build Sidebar HTML ─────────────────────────────────────
  function buildSidebar() {
    var sidebar = document.createElement('aside');
    sidebar.className = 'ng-sidebar';
    sidebar.id = 'ng-sidebar';
    sidebar.setAttribute('role', 'navigation');
    sidebar.setAttribute('aria-label', 'Main navigation');

    // Header
    var header = document.createElement('div');
    header.className = 'ng-sidebar-header';
    header.innerHTML =
      '<div class="ng-sidebar-brand">' +
        '<div class="ng-sidebar-brand-icon">' +
          '<i class="bi bi-diamond-fill" style="font-size:0.875rem"></i>' +
        '</div>' +
        '<div>' +
          '<div class="ng-sidebar-brand-text">SuperLocalMemory</div>' +
          '<div class="ng-sidebar-brand-version" id="ng-version">v3.4.4</div>' +
        '</div>' +
      '</div>';
    sidebar.appendChild(header);

    // Nav
    var nav = document.createElement('nav');
    nav.className = 'ng-sidebar-nav';

    NAV_SECTIONS.forEach(function(section) {
      var sDiv = document.createElement('div');
      sDiv.className = 'ng-sidebar-section';

      var label = document.createElement('div');
      label.className = 'ng-sidebar-section-label';
      label.textContent = section.label;
      sDiv.appendChild(label);

      section.items.forEach(function(item) {
        var a = document.createElement('a');
        a.className = 'ng-sidebar-item';
        a.setAttribute('data-target', item.id);
        a.setAttribute('role', 'tab');
        a.setAttribute('aria-controls', item.id);
        a.setAttribute('tabindex', '0');
        if (item.id === 'dashboard-pane') a.classList.add('active');

        a.innerHTML =
          '<i class="bi ' + item.icon + ' ng-sidebar-icon"></i>' +
          '<span>' + item.text + '</span>' +
          (item.badge ? '<span class="ng-sidebar-badge">' + item.badge + '</span>' : '');

        a.addEventListener('click', function(e) {
          e.preventDefault();
          activateTab(item.id);
        });

        a.addEventListener('keydown', function(e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            activateTab(item.id);
          }
        });

        sDiv.appendChild(a);
      });

      nav.appendChild(sDiv);
    });

    sidebar.appendChild(nav);

    // Footer
    var footer = document.createElement('div');
    footer.className = 'ng-sidebar-footer';

    // Move profile selector from navbar to sidebar footer
    var profileSelect = document.getElementById('profile-select');
    var addProfileBtn = document.getElementById('add-profile-btn');

    footer.innerHTML =
      '<div style="margin-bottom:8px">' +
        '<div class="ng-sidebar-section-label" style="padding:0 0 4px">Profile</div>' +
        '<div style="display:flex;gap:4px;align-items:center" id="ng-profile-container"></div>' +
      '</div>' +
      '<div style="display:flex;gap:4px;align-items:center">' +
        '<button class="ng-btn" id="ng-refresh-btn" title="Refresh" style="flex:1;justify-content:center">' +
          '<i class="bi bi-arrow-clockwise"></i>' +
        '</button>' +
        '<button class="ng-btn" id="ng-theme-toggle" title="Toggle theme" onclick="toggleDarkMode()" style="flex:1;justify-content:center">' +
          '<i class="bi bi-sun-fill" id="ng-theme-icon"></i>' +
        '</button>' +
        '<button class="ng-btn" id="ng-privacy-btn" title="Privacy blur (for screen recording)" onclick="togglePrivacyBlur()" style="flex:1;justify-content:center">' +
          '<i class="bi bi-eye-slash" id="ng-privacy-icon"></i>' +
        '</button>' +
        '<a href="https://github.com/qualixar/superlocalmemory" target="_blank" class="ng-btn" title="Star on GitHub" style="flex:1;justify-content:center">' +
          '<i class="bi bi-github"></i>' +
        '</a>' +
      '</div>';

    sidebar.appendChild(footer);

    return sidebar;
  }

  // ── Restructure DOM ────────────────────────────────────────
  function restructureDOM() {
    var body = document.body;
    // Target the MAIN container-fluid (direct child of body), not the one inside navbar
    var containers = document.querySelectorAll('body > .container-fluid');
    var container = containers.length > 0 ? containers[containers.length - 1] : null;
    if (!container) {
      // Fallback: find the container that holds the tab-content
      container = document.querySelector('.tab-content')?.closest('.container-fluid');
    }
    if (!container) return;

    // Create shell wrapper
    var shell = document.createElement('div');
    shell.className = 'ng-shell';

    // Build and insert sidebar
    var sidebar = buildSidebar();
    shell.appendChild(sidebar);

    // Create content wrapper
    var content = document.createElement('main');
    content.className = 'ng-content';
    var inner = document.createElement('div');
    inner.className = 'ng-content-inner';

    // Move container content into inner
    while (container.firstChild) {
      inner.appendChild(container.firstChild);
    }
    content.appendChild(inner);
    shell.appendChild(content);

    // Move footer into content
    var existingFooter = document.querySelector('footer');
    if (existingFooter) {
      content.appendChild(existingFooter);
    }

    // Replace container with shell
    container.parentNode.replaceChild(shell, container);

    // Move dashboard-only elements INTO the dashboard-pane so they scroll with it
    var dashboardPane = document.getElementById('dashboard-pane');
    if (dashboardPane) {
      ['stats-container', 'privacy-notice', 'feedback-progress'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) dashboardPane.insertBefore(el, dashboardPane.firstChild);
      });
    }

    // Move profile selector to sidebar footer
    var profileContainer = document.getElementById('ng-profile-container');
    var profileSelect = document.getElementById('profile-select');
    var addProfileBtn = document.getElementById('add-profile-btn');
    if (profileContainer && profileSelect) {
      profileSelect.classList.remove('profile-select');
      profileSelect.style.cssText = 'flex:1;font-size:0.8125rem;';
      profileContainer.appendChild(profileSelect);
      if (addProfileBtn) {
        addProfileBtn.className = 'ng-btn';
        addProfileBtn.style.cssText = 'padding:4px 8px;';
        profileContainer.appendChild(addProfileBtn);
      }
    }

    // Wire refresh button
    var refreshBtn = document.getElementById('ng-refresh-btn');
    if (refreshBtn && typeof refreshDashboard === 'function') {
      refreshBtn.addEventListener('click', refreshDashboard);
    }

    // Sync version from dashboard
    setTimeout(function() {
      var dashVer = document.getElementById('dashboard-version');
      var ngVer = document.getElementById('ng-version');
      if (dashVer && ngVer && dashVer.textContent !== '...') {
        ngVer.textContent = 'v' + dashVer.textContent;
      }
    }, 1500);
  }

  // ── Tab Activation ─────────────────────────────────────────
  function activateTab(targetId) {
    // Deactivate all sidebar items
    document.querySelectorAll('.ng-sidebar-item').forEach(function(item) {
      item.classList.remove('active');
      item.setAttribute('aria-selected', 'false');
    });

    // Activate clicked sidebar item
    var activeItem = document.querySelector('.ng-sidebar-item[data-target="' + targetId + '"]');
    if (activeItem) {
      activeItem.classList.add('active');
      activeItem.setAttribute('aria-selected', 'true');
    }

    // Deactivate all tab panes
    document.querySelectorAll('.tab-pane').forEach(function(pane) {
      pane.classList.remove('show', 'active');
    });

    // Activate target pane
    var targetPane = document.getElementById(targetId);
    if (targetPane) {
      targetPane.classList.add('show', 'active');
    }

    // Dispatch Bootstrap tab event for backward compat
    var tabButton = document.getElementById(targetId.replace('-pane', '-tab'));
    if (tabButton) {
      try {
        var event = new Event('shown.bs.tab', { bubbles: true });
        event.target = tabButton;
        event.relatedTarget = null;
        tabButton.dispatchEvent(event);
      } catch (e) {
        // Ignore if event dispatch fails
      }
    }

    // Update URL hash via replaceState (avoids auto-scroll to hash target)
    history.replaceState(null, '', '#' + targetId);

    // Scroll content to top on tab switch
    window.scrollTo({ top: 0, behavior: 'instant' });
    var contentEl = document.querySelector('.ng-content');
    if (contentEl) contentEl.scrollTo({ top: 0, behavior: 'instant' });

    // Dashboard-only elements are inside dashboard-pane, so they auto-hide/show with the tab

    // Trigger data loading for lazy-loaded tabs (immediate + deferred for async-heavy tabs)
    triggerTabLoad(targetId);
    // Deferred retry for tabs that need API data to populate
    setTimeout(function() { triggerTabLoad(targetId); }, 500);

    // Scroll sidebar item into view
    if (activeItem) {
      activeItem.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  }

  // ── Lazy Load Tab Data ─────────────────────────────────────
  function triggerTabLoad(tabId) {
    switch(tabId) {
      case 'graph-pane':
        if (typeof loadGraph === 'function') loadGraph();
        // v3.4.4: Initialize chat panel if not already present
        if (typeof initMemoryChat === 'function' && !document.getElementById('chat-panel')) {
          initMemoryChat();
        }
        break;
      case 'memories-pane':
        if (typeof loadMemories === 'function') loadMemories();
        break;
      case 'clusters-pane':
        if (typeof loadClusters === 'function') loadClusters();
        break;
      case 'patterns-pane':
        if (typeof loadPatterns === 'function') loadPatterns();
        break;
      case 'timeline-pane':
        if (typeof loadTimeline === 'function') loadTimeline();
        break;
      case 'events-pane':
        if (typeof initEventStream === 'function') initEventStream();
        if (typeof loadEventStats === 'function') loadEventStats();
        break;
      case 'agents-pane':
        if (typeof loadAgents === 'function') loadAgents();
        break;
      case 'learning-pane':
        if (typeof loadLearning === 'function') loadLearning();
        break;
      case 'trust-pane':
        if (typeof loadTrustDashboard === 'function') loadTrustDashboard();
        break;
      case 'lifecycle-pane':
        if (typeof loadLifecycle === 'function') loadLifecycle();
        break;
      case 'behavioral-pane':
        if (typeof loadBehavioral === 'function') loadBehavioral();
        break;
      case 'compliance-pane':
        if (typeof loadCompliance === 'function') loadCompliance();
        break;
      case 'math-health-pane':
        if (typeof loadMathHealth === 'function') loadMathHealth();
        break;
      case 'ide-pane':
        if (typeof loadIDEStatus === 'function') loadIDEStatus();
        break;
      case 'health-pane':
        if (typeof loadHealthMonitor === 'function') loadHealthMonitor();
        break;
      case 'ingestion-pane':
        if (typeof loadIngestionStatus === 'function') loadIngestionStatus();
        break;
      case 'entities-pane':
        if (typeof loadEntityExplorer === 'function') loadEntityExplorer();
        break;
      case 'mesh-pane':
        if (typeof loadMeshPeers === 'function') loadMeshPeers();
        break;
      case 'settings-pane':
        if (typeof loadSettings === 'function') loadSettings();
        if (typeof loadModeSettings === 'function') loadModeSettings();
        if (typeof loadAutoSettings === 'function') loadAutoSettings();
        if (typeof updateModeUI === 'function') updateModeUI();
        break;
    }
  }

  // ── Hash-based Routing ─────────────────────────────────────
  function handleHash() {
    var hash = window.location.hash.replace('#', '');
    if (hash && document.getElementById(hash)) {
      activateTab(hash);
    }
  }

  // ── Theme Application ───────────────────────────────────────
  function applyNgTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    // ng-dark class ONLY in dark mode — light mode uses Bootstrap defaults
    if (theme === 'dark') {
      document.body.classList.add('ng-dark');
    } else {
      document.body.classList.remove('ng-dark');
    }
    // Update both icons (original + sidebar)
    var icon = document.getElementById('theme-icon');
    if (icon) icon.className = theme === 'dark' ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
    var ngIcon = document.getElementById('ng-theme-icon');
    if (ngIcon) ngIcon.className = theme === 'dark' ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';

    // Fix inline styles that conflict with dark/light mode (setProperty needed to override inline styles)
    var themedElements = ['graph-container', 'memory-timeline-chart'];
    themedElements.forEach(function(id) {
      var el = document.getElementById(id);
      if (!el) return;
      if (theme === 'dark') {
        el.style.setProperty('background', '#0f1012', 'important');
        el.style.setProperty('background-color', '#0f1012', 'important');
        el.style.setProperty('border-color', 'rgba(255,255,255,0.06)', 'important');
      } else {
        el.style.setProperty('background', '#ffffff', 'important');
        el.style.setProperty('background-color', '#ffffff', 'important');
        el.style.setProperty('border-color', '#e5e7eb', 'important');
      }
    });

    // Also fix graph label colors for readability
    var graphLabels = document.querySelectorAll('.node-label');
    graphLabels.forEach(function(l) {
      l.style.fill = theme === 'dark' ? '#ccc' : '#333';
    });
  }

  // ── Initialize ─────────────────────────────────────────────
  function init() {
    // Respect saved theme or auto-detect
    var savedTheme = localStorage.getItem('slm-theme');
    if (!savedTheme) {
      savedTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    applyNgTheme(savedTheme);

    // Override toggleDarkMode — syncs Bootstrap theme + ng-dark class
    window.toggleDarkMode = function() {
      var current = document.documentElement.getAttribute('data-bs-theme');
      var next = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem('slm-theme', next);
      applyNgTheme(next);
    };

    // Restructure DOM
    restructureDOM();

    // Handle initial hash — run synchronously, no timeout race
    if (window.location.hash) {
      handleHash();
    }

    // Listen for hash changes
    window.addEventListener('hashchange', handleHash);

    // toggleDarkMode already overridden above with theme toggle support

    // Privacy blur toggle for screen recording
    window.togglePrivacyBlur = function() {
      document.body.classList.toggle('ng-privacy-blur');
      var icon = document.getElementById('ng-privacy-icon');
      var isBlurred = document.body.classList.contains('ng-privacy-blur');
      if (icon) icon.className = isBlurred ? 'bi bi-eye' : 'bi bi-eye-slash';
    };

    // Auto-enable blur if URL has ?blur=1
    if (window.location.search.indexOf('blur=1') >= 0) {
      document.body.classList.add('ng-privacy-blur');
    }
  }

  // Run when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
