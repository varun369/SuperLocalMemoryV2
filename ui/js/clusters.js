// SuperLocalMemory V2 - Clusters View
// Depends on: core.js
//
// Security: All dynamic values escaped via escapeHtml(). Data from local DB only.

async function loadClusters() {
    showLoading('clusters-list', 'Loading clusters...');
    try {
        var response = await fetch('/api/clusters');
        var data = await response.json();
        renderClusters(data.clusters);
    } catch (error) {
        console.error('Error loading clusters:', error);
        showEmpty('clusters-list', 'collection', 'Failed to load clusters');
    }
}

function renderClusters(clusters) {
    var container = document.getElementById('clusters-list');
    if (!clusters || clusters.length === 0) {
        showEmpty('clusters-list', 'collection', 'No clusters found. Run "slm build-graph" to generate clusters.');
        return;
    }

    var colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a'];
    container.textContent = '';

    clusters.forEach(function(cluster, idx) {
        var color = colors[idx % colors.length];

        var card = document.createElement('div');
        card.className = 'card cluster-card';
        card.style.cssText = 'border-color:' + color + '; cursor:pointer;';
        card.setAttribute('data-cluster-id', cluster.cluster_id);
        card.title = 'Click to filter graph to this cluster';

        var body = document.createElement('div');
        body.className = 'card-body';

        var title = document.createElement('h6');
        title.className = 'card-title';
        title.textContent = 'Cluster ' + cluster.cluster_id + ' ';
        var countBadge = document.createElement('span');
        countBadge.className = 'badge bg-secondary float-end';
        countBadge.textContent = cluster.member_count + ' memories';
        title.appendChild(countBadge);
        body.appendChild(title);

        var imp = document.createElement('p');
        imp.className = 'mb-2';
        imp.textContent = 'Avg Importance: ' + parseFloat(cluster.avg_importance).toFixed(1);
        body.appendChild(imp);

        var cats = document.createElement('p');
        cats.className = 'mb-2';
        cats.textContent = 'Categories: ' + (cluster.categories || 'None');
        body.appendChild(cats);

        var entLabel = document.createElement('strong');
        entLabel.textContent = 'Top Entities:';
        body.appendChild(entLabel);
        body.appendChild(document.createElement('br'));

        if (cluster.top_entities && cluster.top_entities.length > 0) {
            cluster.top_entities.forEach(function(e) {
                var badge = document.createElement('span');
                badge.className = 'badge bg-info entity-badge';
                badge.textContent = e.entity + ' (' + e.count + ')';
                body.appendChild(badge);
                body.appendChild(document.createTextNode(' '));
            });
        } else {
            var none = document.createElement('span');
            none.className = 'text-muted';
            none.textContent = 'No entities';
            body.appendChild(none);
        }

        card.appendChild(body);
        container.appendChild(card);

        // v2.6.5: Click card → filter graph to this cluster
        card.addEventListener('click', function(e) {
            // Don't trigger if clicking on badge or entity
            if (e.target.classList.contains('entity-badge') || e.target.classList.contains('badge')) {
                return;
            }

            const clusterId = parseInt(card.getAttribute('data-cluster-id'));
            filterGraphToCluster(clusterId);
        });

        // v2.6.5: Click entity badge → filter graph by entity
        if (cluster.top_entities && cluster.top_entities.length > 0) {
            const entityBadges = body.querySelectorAll('.entity-badge');
            entityBadges.forEach(function(badge) {
                badge.style.cursor = 'pointer';
                badge.title = 'Click to show memories with this entity';
                badge.addEventListener('click', function(e) {
                    e.stopPropagation(); // Don't trigger card click
                    const entityText = badge.textContent.split(' (')[0]; // Extract entity name
                    filterGraphByEntity(entityText);
                });
            });
        }

        // v2.6.5: Click "X memories" badge → show list in sidebar (future feature)
        countBadge.style.cursor = 'pointer';
        countBadge.title = 'Click to view memories in this cluster';
        countBadge.addEventListener('click', function(e) {
            e.stopPropagation(); // Don't trigger card click
            showClusterMemories(cluster.cluster_id);
        });
    });
}

// v2.6.5: Filter graph to a specific cluster
function filterGraphToCluster(clusterId) {
    // Switch to Graph tab
    const graphTab = document.querySelector('a[href="#graph"]');
    if (graphTab) {
        graphTab.click();
    }

    // Apply filter after a delay (for tab to load)
    setTimeout(function() {
        if (typeof filterState !== 'undefined' && typeof filterByCluster === 'function' && typeof renderGraph === 'function') {
            filterState.cluster_id = clusterId;
            const filtered = filterByCluster(originalGraphData, clusterId);
            renderGraph(filtered);

            // Update URL
            const url = new URL(window.location);
            url.searchParams.set('cluster_id', clusterId);
            window.history.replaceState({}, '', url);
        }
    }, 300);
}

// v2.6.5: Filter graph by entity
function filterGraphByEntity(entity) {
    // Switch to Graph tab
    const graphTab = document.querySelector('a[href="#graph"]');
    if (graphTab) {
        graphTab.click();
    }

    // Apply filter after a delay
    setTimeout(function() {
        if (typeof filterState !== 'undefined' && typeof filterByEntity === 'function' && typeof renderGraph === 'function') {
            filterState.entity = entity;
            const filtered = filterByEntity(originalGraphData, entity);
            renderGraph(filtered);
        }
    }, 300);
}

// v2.6.5: Show memories in a cluster (future: sidebar list)
function showClusterMemories(clusterId) {
    // For now, just filter Memories tab
    const memoriesTab = document.querySelector('a[href="#memories"]');
    if (memoriesTab) {
        memoriesTab.click();
    }

    // TODO: Implement sidebar memory list view
    console.log('Show memories for cluster', clusterId);
    showToast('Filtering memories for cluster ' + clusterId);
}
