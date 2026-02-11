// SuperLocalMemory V2 - Search
// Depends on: core.js, memories.js (renderMemoriesTable, loadMemories)

var lastSearchResults = null;

async function searchMemories() {
    var query = document.getElementById('search-query').value;
    if (!query.trim()) { loadMemories(); return; }

    showLoading('memories-list', 'Searching...');
    try {
        var response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, limit: 20, min_score: 0.3 })
        });
        var data = await response.json();

        var results = data.results || [];
        results.sort(function(a, b) { return (b.score || 0) - (a.score || 0); });

        lastSearchResults = results;

        var exportBtn = document.getElementById('export-search-btn');
        if (exportBtn) exportBtn.style.display = results.length > 0 ? '' : 'none';

        renderMemoriesTable(results, true);
    } catch (error) {
        console.error('Error searching:', error);
        showEmpty('memories-list', 'exclamation-triangle', 'Search failed. Please try again.');
    }
}

// ============================================================================
// Export All / Search Results
// ============================================================================

function exportAll(format) {
    var url = '/api/export?format=' + encodeURIComponent(format);
    var category = document.getElementById('filter-category').value;
    var project = document.getElementById('filter-project').value;
    if (category) url += '&category=' + encodeURIComponent(category);
    if (project) url += '&project_name=' + encodeURIComponent(project);
    window.location.href = url;
}

function exportSearchResults() {
    if (!lastSearchResults || lastSearchResults.length === 0) {
        showToast('No search results to export');
        return;
    }
    var content = JSON.stringify({
        exported_at: new Date().toISOString(),
        query: document.getElementById('search-query').value,
        total: lastSearchResults.length,
        results: lastSearchResults
    }, null, 2);
    downloadFile('search-results-' + Date.now() + '.json', content, 'application/json');
}
