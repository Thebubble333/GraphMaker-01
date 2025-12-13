// utils/geometry_logic.js

const svg = document.getElementById('geo-canvas');
let selectedElement = null;
let dragMode = null; // 'VERTEX', 'SHAPE'
let startMouse = {x:0, y:0};
let activeShapeId = null;
let activeVertexIdx = null;

// Helper: Convert screen point to SVG point
function getMousePos(evt) {
    const CTM = svg.getScreenCTM();
    return {
        x: (evt.clientX - CTM.e) / CTM.a,
        y: (evt.clientY - CTM.f) / CTM.d
    };
}

function render() {
    svg.innerHTML = ''; // Clear canvas
    
    // Draw Shapes
    SHAPES.forEach(shape => {
        const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
        group.setAttribute('class', 'shape-group');
        group.style.cursor = 'move';
        
        // 1. Draw Polygon Body (Fill)
        const poly = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        const ptsStr = shape.points.map(p => `${p.x},${p.y}`).join(" ");
        poly.setAttribute("points", ptsStr);
        poly.setAttribute("fill", shape.color);
        poly.setAttribute("stroke", shape.stroke);
        poly.setAttribute("stroke-width", shape.stroke_width);
        poly.setAttribute("fill-opacity", "0.8");
        
        // Event: Drag Shape
        poly.addEventListener('mousedown', (e) => {
            e.stopPropagation();
            startDragShape(e, shape);
        });
        
        group.appendChild(poly);
        
        // 2. Draw Vertices (Circles)
        if(shape.show_vertices) {
            shape.points.forEach((p, idx) => {
                const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                c.setAttribute("cx", p.x);
                c.setAttribute("cy", p.y);
                c.setAttribute("r", 6); // Hit radius
                c.setAttribute("fill", "rgba(0,0,0,0.5)");
                c.setAttribute("stroke", "white");
                c.setAttribute("stroke-width", "2");
                c.style.cursor = 'crosshair';
                
                // Event: Drag Vertex
                c.addEventListener('mousedown', (e) => {
                    e.stopPropagation();
                    startDragVertex(e, shape, idx);
                });
                
                group.appendChild(c);
            });
        }
        
        // 3. Draw ID Label (Center)
        // Simple bounding box center
        if(shape.points.length > 0) {
            let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
            shape.points.forEach(p => {
                if(p.x < minX) minX = p.x;
                if(p.x > maxX) maxX = p.x;
                if(p.y < minY) minY = p.y;
                if(p.y > maxY) maxY = p.y;
            });
            const cx = (minX + maxX)/2;
            const cy = (minY + maxY)/2;
            
            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("x", cx);
            text.setAttribute("y", cy);
            text.setAttribute("text-anchor", "middle");
            text.setAttribute("dominant-baseline", "middle");
            text.setAttribute("fill", "black");
            text.setAttribute("font-size", "12");
            text.setAttribute("pointer-events", "none");
            text.textContent = shape.label || `Shape ${shape.id}`;
            group.appendChild(text);
        }

        svg.appendChild(group);
    });
}

// --- ACTIONS ---

function startDragShape(e, shape) {
    dragMode = 'SHAPE';
    activeShapeId = shape.id;
    startMouse = getMousePos(e);
}

function startDragVertex(e, shape, idx) {
    dragMode = 'VERTEX';
    activeShapeId = shape.id;
    activeVertexIdx = idx;
    startMouse = getMousePos(e);
}

window.addEventListener('mousemove', (e) => {
    if(!dragMode) return;
    e.preventDefault();
    
    const mouse = getMousePos(e);
    const dx = mouse.x - startMouse.x;
    const dy = mouse.y - startMouse.y;
    
    // Find active shape
    const shape = SHAPES.find(s => s.id === activeShapeId);
    if(!shape) return;

    if(dragMode === 'SHAPE') {
        // Move all points
        shape.points.forEach(p => {
            p.x += dx;
            p.y += dy;
        });
    } else if (dragMode === 'VERTEX') {
        // Move specific point
        const p = shape.points[activeVertexIdx];
        p.x += dx;
        p.y += dy;
    }
    
    render();
    startMouse = mouse;
});

window.addEventListener('mouseup', () => {
    dragMode = null;
    activeShapeId = null;
    activeVertexIdx = null;
});

// Initial Render
render();