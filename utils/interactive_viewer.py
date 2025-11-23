import streamlit.components.v1 as components
import base64


def render_interactive_graph(svg_string: str, width_px: float, height_px: float, target_width_cm: float,
                             target_height_cm: float, scale_choice: int):
    """
    Renders the SVG inside a self-contained HTML block with JavaScript.
    The JS handles:
      1. Dragging elements with class 'draggable-label'
      2. Exporting the *current* state (post-drag) to PNG or SVG
      3. Persisting drag locations across Streamlit re-runs via sessionStorage
    """

    # Escape single quotes in SVG for JS string
    svg_safe = svg_string.replace("`", "\`")

    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            .graph-container {{
                width: 100%;
                /* INCREASED HEIGHT: Taller view window */
                height: 85vh; 
                overflow: auto;
                background: white;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                justify-content: center;
                align-items: flex-start;
                padding: 10px;
                position: relative;
            }}

            svg {{
                max-width: 100%;
                height: auto;
                box-shadow: 0 0 5px rgba(0,0,0,0.05);
            }}

            /* Style for draggable groups */
            .draggable-label {{
                cursor: grab;
                transition: opacity 0.2s;
            }}
            .draggable-label:hover {{
                opacity: 0.7;
            }}
            .draggable-label:active {{
                cursor: grabbing;
            }}

            .controls {{
                margin-bottom: 10px;
                font-family: sans-serif;
                display: flex;
                gap: 10px;
                align-items: center;
            }}

            .btn {{
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 13px;
                cursor: pointer;
                border-radius: 4px;
                font-weight: 500;
            }}

            .btn:hover {{
                background-color: #45a049;
            }}

            .btn-reset {{
                background-color: #f44336; 
            }}
            .btn-reset:hover {{
                background-color: #d32f2f;
            }}

            .hint {{
                color: #666;
                font-size: 12px;
                font-style: italic;
            }}
        </style>
    </head>
    <body>

        <div class="controls">
            <button class="btn" onclick="downloadPNG()">Download PNG</button>
            <button class="btn" style="background-color: #2196F3;" onclick="downloadSVG()">Download SVG</button>
            <button class="btn btn-reset" onclick="resetLayout()">Reset Positions</button>
            <span class="hint">💡 Drag labels to move them!</span>
        </div>

        <div class="graph-container" id="graph-container">
            <!-- SVG will be injected here -->
        </div>

        <script>
            // Inject SVG
            const container = document.getElementById('graph-container');
            container.innerHTML = `{svg_safe}`;
            const svg = container.querySelector('svg');

            // --- Persistence Logic ---
            const storageKeyPrefix = "graph_maker_pos_";

            function restorePositions() {{
                const labels = document.querySelectorAll('.draggable-label');
                labels.forEach(el => {{
                    const id = el.id;
                    if (id) {{
                        const stored = sessionStorage.getItem(storageKeyPrefix + id);
                        if (stored) {{
                            try {{
                                const pos = JSON.parse(stored);
                                // Apply translate transform
                                el.setAttribute('transform', `translate(${{pos.x}}, ${{pos.y}})`);
                            }} catch(e) {{
                                console.error("Error parsing stored pos", e);
                            }}
                        }}
                    }}
                }});
            }}

            function resetLayout() {{
                // Clear only our keys
                Object.keys(sessionStorage).forEach(key => {{
                    if(key.startsWith(storageKeyPrefix)) {{
                        sessionStorage.removeItem(key);
                    }}
                }});
                // Reload SVG content (clears transforms)
                container.innerHTML = `{svg_safe}`;
                // Re-attach event listeners (since we wiped DOM)
                const newSvg = container.querySelector('svg');
                attachListeners(newSvg);
            }}

            // --- Drag Logic ---
            let selectedElement = null;
            let offset = {{x: 0, y: 0}};
            let startTransform = {{x: 0, y: 0}};

            function getTranslate(el) {{
                const transform = el.getAttribute('transform');
                if (!transform) return {{x: 0, y: 0}};
                const match = /translate\(([^,]+),([^)]+)\)/.exec(transform);
                if (match) return {{x: parseFloat(match[1]), y: parseFloat(match[2])}};
                return {{x: 0, y: 0}};
            }}

            function makeDraggable(evt) {{
                const el = evt.target.closest('.draggable-label');
                if (el) {{
                    selectedElement = el;
                    const CTM = svg.getScreenCTM();
                    offset.x = (evt.clientX - CTM.e) / CTM.a;
                    offset.y = (evt.clientY - CTM.f) / CTM.d;
                    startTransform = getTranslate(selectedElement);
                }}
            }}

            function drag(evt) {{
                if (selectedElement) {{
                    evt.preventDefault();
                    const CTM = svg.getScreenCTM();
                    const coordX = (evt.clientX - CTM.e) / CTM.a;
                    const coordY = (evt.clientY - CTM.f) / CTM.d;
                    const dx = coordX - offset.x;
                    const dy = coordY - offset.y;
                    const newX = startTransform.x + dx;
                    const newY = startTransform.y + dy;
                    selectedElement.setAttribute('transform', `translate(${{newX}}, ${{newY}})`);
                }}
            }}

            function endDrag() {{
                if (selectedElement) {{
                    // Save position
                    const transform = getTranslate(selectedElement);
                    const id = selectedElement.id;
                    if (id) {{
                        sessionStorage.setItem(storageKeyPrefix + id, JSON.stringify(transform));
                    }}
                    selectedElement = null;
                }}
            }}

            function attachListeners(targetSvg) {{
                targetSvg.addEventListener('mousedown', makeDraggable);
                targetSvg.addEventListener('mousemove', drag);
                targetSvg.addEventListener('mouseup', endDrag);
                targetSvg.addEventListener('mouseleave', endDrag);
                targetSvg.addEventListener('touchstart', (e) => makeDraggable(e.touches[0]));
                targetSvg.addEventListener('touchmove', (e) => drag(e.touches[0]));
                targetSvg.addEventListener('touchend', endDrag);
            }}

            // Init
            attachListeners(svg);
            restorePositions();


            // --- Download Logic ---

            function downloadPNG() {{
                const w = {width_px};
                const h = {height_px};
                const scale = {scale_choice};
                const clone = container.querySelector('svg').cloneNode(true);
                clone.setAttribute('width', w);
                clone.setAttribute('height', h);

                const svgData = new XMLSerializer().serializeToString(clone);
                const img = new Image();
                img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgData)));

                img.onload = function() {{
                    const canvas = document.createElement("canvas");
                    canvas.width = w * scale;
                    canvas.height = h * scale;
                    const ctx = canvas.getContext("2d");
                    ctx.scale(scale, scale);
                    ctx.fillStyle = "white";
                    ctx.fillRect(0, 0, w, h);
                    ctx.drawImage(img, 0, 0, w, h);
                    const link = document.createElement('a');
                    link.download = 'graph_custom.png';
                    link.href = canvas.toDataURL("image/png");
                    link.click();
                }};
            }}

            function downloadSVG() {{
                const clone = container.querySelector('svg').cloneNode(true);
                clone.setAttribute('width', '{target_width_cm}cm');
                clone.setAttribute('height', '{target_height_cm}cm');
                const svgData = new XMLSerializer().serializeToString(clone);
                const blob = new Blob([svgData], {{type: "image/svg+xml;charset=utf-8"}});
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'graph_custom.svg';
                link.click();
            }}

        </script>
    </body>
    </html>
    """

    # Render with scrolling enabled
    # INCREASED IFRAME HEIGHT: Matches the new CSS height + controls
    components.html(html_code, height=900, scrolling=True)