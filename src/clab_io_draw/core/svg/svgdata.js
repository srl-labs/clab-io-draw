/**
 * Adds metadata and IDs in the SVG export.
 */
Draw.loadPlugin(function(ui) {
    var graphCreateSvgImageExport = Graph.prototype.createSvgImageExport;
    Graph.prototype.createSvgImageExport = function() {
        var exp = graphCreateSvgImageExport.apply(this, arguments);
        var expDrawCellState = exp.drawCellState;
        exp.drawCellState = function(state, canvas) {
            var svgDoc = canvas.root.ownerDocument;
            var g = (svgDoc.createElementNS != null) ?
                svgDoc.createElementNS(mxConstants.NS_SVG, 'g') : svgDoc.createElement('g');
            g.setAttribute('id', 'cell-' + state.cell.id);
            var prev = canvas.root;
            prev.appendChild(g);
            canvas.root = g;
            expDrawCellState.apply(this, arguments);
            if (g.firstChild == null) {
                g.parentNode.removeChild(g);
            } else if (mxUtils.isNode(state.cell.value)) {
                g.setAttribute('content', mxUtils.getXml(state.cell.value));
                for (var i = 0; i < state.cell.value.attributes.length; i++) {
                    var attrib = state.cell.value.attributes[i];
                    g.setAttribute('data-' + attrib.name, attrib.value);
                }
            }
            canvas.root = prev;
        };
        return exp;
    };
});
