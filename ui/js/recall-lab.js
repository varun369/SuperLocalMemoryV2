// SuperLocalMemory V3 — Recall Lab
// Part of Qualixar | https://superlocalmemory.com

document.getElementById('recall-lab-search')?.addEventListener('click', function() {
    var query = document.getElementById('recall-lab-query').value.trim();
    if (!query) return;

    var resultsDiv = document.getElementById('recall-lab-results');
    var metaDiv = document.getElementById('recall-lab-meta');
    resultsDiv.textContent = '';
    var spinner = document.createElement('div');
    spinner.className = 'text-center';
    var spinnerInner = document.createElement('div');
    spinnerInner.className = 'spinner-border text-primary';
    spinner.appendChild(spinnerInner);
    resultsDiv.appendChild(spinner);

    fetch('/api/v3/recall/trace', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: query, limit: 10})
    }).then(function(r) { return r.json(); }).then(function(data) {
        if (data.error) {
            resultsDiv.textContent = '';
            var errDiv = document.createElement('div');
            errDiv.className = 'alert alert-danger';
            errDiv.textContent = data.error;
            resultsDiv.appendChild(errDiv);
            return;
        }

        metaDiv.textContent = '';
        appendMetaField(metaDiv, 'Query type: ', data.query_type || 'unknown');
        metaDiv.appendChild(document.createTextNode(' | '));
        appendMetaField(metaDiv, 'Results: ', String(data.result_count));
        metaDiv.appendChild(document.createTextNode(' | '));
        appendMetaField(metaDiv, 'Time: ', (data.retrieval_time_ms || 0).toFixed(0) + 'ms');

        if (!data.results || data.results.length === 0) {
            resultsDiv.textContent = '';
            var infoDiv = document.createElement('div');
            infoDiv.className = 'alert alert-info';
            infoDiv.textContent = 'No results found.';
            resultsDiv.appendChild(infoDiv);
            return;
        }

        resultsDiv.textContent = '';
        var listGroup = document.createElement('div');
        listGroup.className = 'list-group';

        data.results.forEach(function(r, i) {
            var channels = r.channel_scores || {};
            var maxChannel = Math.max(channels.semantic || 0, channels.bm25 || 0, channels.entity_graph || 0, channels.temporal || 0) || 1;

            var item = document.createElement('div');
            item.className = 'list-group-item list-group-item-action';
            item.style.cursor = 'pointer';
            item.title = 'Click to view full memory';
            (function(result) {
                item.addEventListener('click', function() {
                    if (typeof openMemoryDetail === 'function') {
                        openMemoryDetail({
                            id: result.fact_id,
                            content: result.content,
                            score: result.score,
                            importance: Math.round((result.confidence || 0.5) * 10),
                            category: 'recall',
                            tags: Object.keys(result.channel_scores || {}).join(', '),
                            created_at: null,
                            trust_score: result.trust_score,
                            channel_scores: result.channel_scores
                        });
                    }
                });
            })(r);

            var header = document.createElement('h6');
            header.className = 'mb-1';
            header.textContent = (i + 1) + '. ' + (r.content || '').substring(0, 200);
            item.appendChild(header);

            var meta = document.createElement('small');
            meta.className = 'text-muted';
            meta.textContent = 'Score: ' + r.score + ' | Trust: ' + r.trust_score + ' | Confidence: ' + r.confidence;
            item.appendChild(meta);

            var barsDiv = document.createElement('div');
            barsDiv.className = 'mt-2';
            barsDiv.appendChild(buildChannelBar('Semantic', channels.semantic || 0, maxChannel, 'primary'));
            barsDiv.appendChild(buildChannelBar('BM25', channels.bm25 || 0, maxChannel, 'success'));
            barsDiv.appendChild(buildChannelBar('Entity', channels.entity_graph || 0, maxChannel, 'info'));
            barsDiv.appendChild(buildChannelBar('Temporal', channels.temporal || 0, maxChannel, 'warning'));
            item.appendChild(barsDiv);

            listGroup.appendChild(item);
        });
        resultsDiv.appendChild(listGroup);
    }).catch(function(e) {
        resultsDiv.textContent = '';
        var errDiv = document.createElement('div');
        errDiv.className = 'alert alert-danger';
        errDiv.textContent = 'Error: ' + e.message;
        resultsDiv.appendChild(errDiv);
    });
});

function appendMetaField(parent, label, value) {
    var text = document.createTextNode(label);
    parent.appendChild(text);
    var strong = document.createElement('strong');
    strong.textContent = value;
    parent.appendChild(strong);
}

function buildChannelBar(name, score, max, color) {
    var pct = max > 0 ? Math.round((score / max) * 100) : 0;

    var row = document.createElement('div');
    row.className = 'd-flex align-items-center mb-1';

    var label = document.createElement('span');
    label.className = 'me-2';
    label.style.width = '70px';
    label.style.fontSize = '0.75rem';
    label.textContent = name;
    row.appendChild(label);

    var progressWrap = document.createElement('div');
    progressWrap.className = 'progress flex-grow-1';
    progressWrap.style.height = '14px';

    var bar = document.createElement('div');
    bar.className = 'progress-bar bg-' + color;
    bar.style.width = pct + '%';
    bar.textContent = score.toFixed(3);
    progressWrap.appendChild(bar);

    row.appendChild(progressWrap);
    return row;
}

// Enter key support
document.getElementById('recall-lab-query')?.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('recall-lab-search')?.click();
});
