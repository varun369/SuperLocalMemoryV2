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
        card.style.borderColor = color;

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
    });
}
