// SuperLocalMemory V2 - Knowledge Graph (D3.js force-directed)
// Depends on: core.js, modal.js (openMemoryDetail)

var graphData = { nodes: [], links: [] };

async function loadGraph() {
    var maxNodes = document.getElementById('graph-max-nodes').value;
    try {
        var response = await fetch('/api/graph?max_nodes=' + maxNodes);
        graphData = await response.json();
        renderGraph(graphData);
    } catch (error) {
        console.error('Error loading graph:', error);
    }
}

function renderGraph(data) {
    var container = document.getElementById('graph-container');
    container.textContent = '';
    var width = container.clientWidth || 1200;
    var height = 600;
    var svg = d3.select('#graph-container').append('svg').attr('width', width).attr('height', height);
    var tooltip = d3.select('body').append('div').attr('class', 'tooltip-custom').style('opacity', 0);
    var colorScale = d3.scaleOrdinal(d3.schemeCategory10);
    var simulation = d3.forceSimulation(data.nodes).force('link', d3.forceLink(data.links).id(function(d) { return d.id; }).distance(100)).force('charge', d3.forceManyBody().strength(-200)).force('center', d3.forceCenter(width / 2, height / 2)).force('collision', d3.forceCollide().radius(20));
    var link = svg.append('g').selectAll('line').data(data.links).enter().append('line').attr('class', 'link').attr('stroke-width', function(d) { return Math.sqrt(d.weight * 2); });
    var node = svg.append('g').selectAll('circle').data(data.nodes).enter().append('circle').attr('class', 'node').attr('r', function(d) { return 5 + (d.importance || 5); }).attr('fill', function(d) { return colorScale(d.cluster_id || 0); }).call(d3.drag().on('start', dragStarted).on('drag', dragged).on('end', dragEnded)).on('mouseover', function(event, d) { tooltip.transition().duration(200).style('opacity', .9); var label = d.category || d.project_name || 'Memory #' + d.id; tooltip.text(label + ': ' + (d.content_preview || d.summary || 'No content')).style('left', (event.pageX + 10) + 'px').style('top', (event.pageY - 28) + 'px'); }).on('mouseout', function() { tooltip.transition().duration(500).style('opacity', 0); }).on('click', function(event, d) { openMemoryDetail(d); });
    simulation.on('tick', function() { link.attr('x1', function(d) { return d.source.x; }).attr('y1', function(d) { return d.source.y; }).attr('x2', function(d) { return d.target.x; }).attr('y2', function(d) { return d.target.y; }); node.attr('cx', function(d) { return d.x; }).attr('cy', function(d) { return d.y; }); });
    function dragStarted(event, d) { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
    function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
    function dragEnded(event, d) { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }
}
