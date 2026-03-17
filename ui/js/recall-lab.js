// SuperLocalMemory V3 — Recall Lab with Pagination
// Part of Qualixar | https://superlocalmemory.com

var recallLabState = {
    allResults: [],
    page: 0,
    perPage: 10,
    query: '',
};

document.getElementById('recall-lab-search')?.addEventListener('click', function() {
    var query = document.getElementById('recall-lab-query').value.trim();
    if (!query) return;

    recallLabState.query = query;
    recallLabState.page = 0;
    var perPageEl = document.getElementById('recall-lab-per-page');
    recallLabState.perPage = perPageEl ? parseInt(perPageEl.value) : 10;
    var fetchLimit = Math.max(recallLabState.perPage * 5, 50); // Fetch up to 5 pages

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
        body: JSON.stringify({query: query, limit: fetchLimit})
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
        appendMetaField(metaDiv, 'Results: ', String((data.results || []).length));
        metaDiv.appendChild(document.createTextNode(' | '));
        appendMetaField(metaDiv, 'Time: ', (data.retrieval_time_ms || 0).toFixed(0) + 'ms');

        recallLabState.allResults = data.results || [];

        if (recallLabState.allResults.length === 0) {
            resultsDiv.textContent = '';
            var infoDiv = document.createElement('div');
            infoDiv.className = 'alert alert-info';
            infoDiv.textContent = 'No results found.';
            resultsDiv.appendChild(infoDiv);
            return;
        }

        renderRecallPage();
    }).catch(function(e) {
        resultsDiv.textContent = '';
        var errDiv = document.createElement('div');
        errDiv.className = 'alert alert-danger';
        errDiv.textContent = 'Error: ' + e.message;
        resultsDiv.appendChild(errDiv);
    });
});

function renderRecallPage() {
    var resultsDiv = document.getElementById('recall-lab-results');
    resultsDiv.textContent = '';

    var results = recallLabState.allResults;
    var start = recallLabState.page * recallLabState.perPage;
    var end = Math.min(start + recallLabState.perPage, results.length);
    var pageResults = results.slice(start, end);
    var totalPages = Math.ceil(results.length / recallLabState.perPage);

    var listGroup = document.createElement('div');
    listGroup.className = 'list-group';

    pageResults.forEach(function(r, i) {
        var globalIndex = start + i;
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
        header.textContent = (globalIndex + 1) + '. ' + (r.content || '').substring(0, 200);
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

    // Pagination controls
    if (totalPages > 1) {
        var nav = document.createElement('nav');
        nav.className = 'mt-3';
        nav.setAttribute('aria-label', 'Recall results pagination');
        var ul = document.createElement('ul');
        ul.className = 'pagination justify-content-center';

        // Prev
        var prevLi = document.createElement('li');
        prevLi.className = 'page-item' + (recallLabState.page === 0 ? ' disabled' : '');
        var prevA = document.createElement('a');
        prevA.className = 'page-link';
        prevA.href = '#';
        prevA.textContent = 'Previous';
        prevA.addEventListener('click', function(e) {
            e.preventDefault();
            if (recallLabState.page > 0) {
                recallLabState.page--;
                renderRecallPage();
            }
        });
        prevLi.appendChild(prevA);
        ul.appendChild(prevLi);

        // Page numbers
        for (var p = 0; p < totalPages; p++) {
            var li = document.createElement('li');
            li.className = 'page-item' + (p === recallLabState.page ? ' active' : '');
            var a = document.createElement('a');
            a.className = 'page-link';
            a.href = '#';
            a.textContent = String(p + 1);
            (function(pageNum) {
                a.addEventListener('click', function(e) {
                    e.preventDefault();
                    recallLabState.page = pageNum;
                    renderRecallPage();
                });
            })(p);
            li.appendChild(a);
            ul.appendChild(li);
        }

        // Next
        var nextLi = document.createElement('li');
        nextLi.className = 'page-item' + (recallLabState.page >= totalPages - 1 ? ' disabled' : '');
        var nextA = document.createElement('a');
        nextA.className = 'page-link';
        nextA.href = '#';
        nextA.textContent = 'Next';
        nextA.addEventListener('click', function(e) {
            e.preventDefault();
            if (recallLabState.page < totalPages - 1) {
                recallLabState.page++;
                renderRecallPage();
            }
        });
        nextLi.appendChild(nextA);
        ul.appendChild(nextLi);

        nav.appendChild(ul);
        resultsDiv.appendChild(nav);

        // Page info
        var info = document.createElement('div');
        info.className = 'text-center text-muted small';
        info.textContent = 'Showing ' + (start + 1) + '-' + end + ' of ' + results.length + ' results';
        resultsDiv.appendChild(info);
    }
}

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
