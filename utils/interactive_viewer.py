import streamlit.components.v1 as components
import base64

def render_interactive_graph(svg_string: str, width_px: float, height_px: float, target_width_cm: float,
                             target_height_cm: float, scale_choice: int):
    """
    Renders SVG with Drag-and-Drop Labels, Client-Side Cropping, and Zoom Controls.
    FIXED: applyCrop now respects manual selection instead of resetting to auto-fit.
    """

    svg_safe = svg_string.replace("`", "\`")

    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            :root {{
                --overlay-color: rgba(0, 0, 0, 0.5);
                --crop-border: 2px dashed #ff0055;
            }}

            body {{
                margin: 0;
                padding: 0;
                background-color: white; 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }}

            .graph-container {{
                width: 100%;
                height: 85vh; 
                overflow: hidden; 
                background: #f0f2f6; 
                border-radius: 5px;
                box-shadow: inset 0 0 10px rgba(0,0,0,0.05);
                display: flex;
                justify-content: center;
                align-items: center; 
                position: relative;
                user-select: none;
            }}

            .svg-wrapper {{
                position: relative;
                display: inline-block;
                background: white;
                box-shadow: 0 10px 25px rgba(0,0,0,0.1); 
                transition: transform 0.2s ease; 
                transform-origin: center center;
            }}

            svg {{
                display: block;
                max-width: none;
                width: 100%;
                height: 100%;
            }}

            /* Draggable Labels */
            .draggable-label {{
                cursor: grab;
                transition: opacity 0.2s;
            }}
            .draggable-label:hover {{ opacity: 0.7; }}
            .draggable-label:active {{ cursor: grabbing; }}

            /* Controls Bar */
            .controls {{
                padding: 10px 15px;
                background: white;
                border-bottom: 1px solid #ddd;
                display: flex;
                gap: 12px;
                align-items: center;
                flex-wrap: wrap;
                position: sticky;
                top: 0;
                z-index: 1000;
            }}

            .btn {{
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 12px;
                text-align: center;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                font-size: 14px;
                cursor: pointer;
                border-radius: 4px;
                font-weight: 500;
                white-space: nowrap;
                min-width: 32px;
                transition: all 0.2s;
            }}
            .btn-blue {{ background-color: #2196F3; }}
            .btn-red {{ background-color: #f44336; }}
            .btn-purple {{ background-color: #9c27b0; }}
            .btn-grey {{ background-color: #607d8b; }}
            .btn-orange {{ background-color: #FF9800; }}
            
            .btn:hover {{ filter: brightness(90%); transform: translateY(-1px); }}
            .btn:active {{ transform: translateY(1px); }}

            .control-group {{
                display: flex;
                gap: 6px;
                align-items: center;
                padding-left: 12px;
                border-left: 1px solid #ddd;
            }}

            /* CROP OVERLAY */
            #crop-layer {{
                display: none;
                position: absolute;
                top: 0; left: 0; width: 100%; height: 100%;
                z-index: 999;
            }}

            #crop-box {{
                position: absolute;
                border: var(--crop-border);
                box-shadow: 0 0 0 9999px var(--overlay-color);
                cursor: move;
                box-sizing: border-box; 
            }}

            .resize-handle {{
                position: absolute;
                width: 14px;
                height: 14px;
                background: #ff0055;
                border: 2px solid white;
                border-radius: 50%;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                z-index: 1001; 
            }}
            .rh-nw {{ top: -7px; left: -7px; cursor: nw-resize; }}
            .rh-ne {{ top: -7px; right: -7px; cursor: ne-resize; }}
            .rh-sw {{ bottom: -7px; left: -7px; cursor: sw-resize; }}
            .rh-se {{ bottom: -7px; right: -7px; cursor: se-resize; }}

        </style>
    </head>
    <body>

        <div class="controls">
            <button class="btn" onclick="downloadPNG()" title="Download PNG Image">PNG</button>
            <button class="btn btn-blue" onclick="downloadSVG()" title="Download Scalable Vector">SVG</button>
            
            <div class="control-group">
                <button class="btn btn-orange" onclick="autoCrop()" title="Snap view to content">✨ Auto Fit</button>
                <button class="btn btn-purple" id="btn-crop-tool" onclick="toggleCropTool()">✂️ Manual</button>
                <button class="btn btn-purple" id="btn-apply-crop" onclick="applyCrop()" style="display:none;">✅ Apply</button>
            </div>

            <div class="control-group">
                <button class="btn btn-grey" onclick="zoomOut()" title="Zoom Out (20%)">➖</button>
                <button class="btn btn-grey" onclick="zoomIn()" title="Zoom In (20%)">➕</button>
                <button class="btn btn-red" onclick="resetAll()" title="Reset Zoom, Crop and Positions">Reset</button>
            </div>

            <div style="flex-grow:1;"></div>
            <span style="color:#888; font-size:12px;" id="status-text">v3.2</span>
        </div>

        <div class="graph-container">
            <div class="svg-wrapper" id="svg-wrapper">
                <div id="crop-layer">
                    <div id="crop-box">
                        <div class="resize-handle rh-nw" data-dir="nw"></div>
                        <div class="resize-handle rh-ne" data-dir="ne"></div>
                        <div class="resize-handle rh-sw" data-dir="sw"></div>
                        <div class="resize-handle rh-se" data-dir="se"></div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const container = document.querySelector('.graph-container');
            const wrapper = document.getElementById('svg-wrapper');
            const cropLayer = document.getElementById('crop-layer');
            const cropBox = document.getElementById('crop-box');
            const btnCropTool = document.getElementById('btn-crop-tool');
            const btnApplyCrop = document.getElementById('btn-apply-crop');
            
            const rawSvg = `{svg_safe}`;
            const parser = new DOMParser();
            const doc = parser.parseFromString(rawSvg, "image/svg+xml");
            const svgEl = doc.documentElement;
            wrapper.prepend(svgEl);

            const ORIG_VIEWBOX_STR = svgEl.getAttribute('viewBox');
            const TARGET_W_CM = {target_width_cm};
            const TARGET_H_CM = {target_height_cm};
            const SCALE_EXPORT = {scale_choice};
            
            let currentZoom = 1.0;
            let cropModeActive = false;

            // --- ZOOM LOGIC ---
            function updateZoomDisplay() {{
                wrapper.style.transform = `scale(${{currentZoom}})`;
                document.getElementById('status-text').innerText = `Zoom: ${{Math.round(currentZoom * 100)}}%`;
            }}

            function zoomIn() {{
                currentZoom *= 1.2; 
                if (currentZoom > 20.0) currentZoom = 20.0;
                updateZoomDisplay();
            }}

            function zoomOut() {{
                currentZoom /= 1.2; 
                if (currentZoom < 0.1) currentZoom = 0.1;
                updateZoomDisplay();
            }}

            // --- AUTO FIT HELPERS ---
            
            // 1. Set ViewBox to the exact content boundary (ignoring infinite graphs)
            function setToBeContentBox() {{
                // A. Temporarily hide the "function-layer" elements
                //    This prevents asymptotes (like 1/x) from blowing up the bounding box
                const graphLines = svgEl.querySelectorAll('.function-layer');
                const restoreList = [];
                
                graphLines.forEach(el => {{
                    restoreList.push({{element: el, originalDisplay: el.style.display}});
                    el.style.display = 'none';
                }});

                // B. Measure the "Safe" content (Grid, Axes, Labels)
                const bbox = svgEl.getBBox();
                
                // C. Restore the graph lines
                restoreList.forEach(item => {{
                    item.element.style.display = item.originalDisplay;
                }});

                const pad = 20;
                const x = bbox.x - pad;
                const y = bbox.y - pad;
                const w = bbox.width + (pad * 2);
                const h = bbox.height + (pad * 2);
                
                // Note the double curly braces for the JS template variables below
                svgEl.setAttribute('viewBox', `${{x}} ${{y}} ${{w}} ${{h}}`);
                svgEl.setAttribute('width', w);
                svgEl.setAttribute('height', h);
            }}

            // 2. Zoom the wrapper so the CURRENT ViewBox fills the container
            function zoomToFitContainer() {{
                // Get current SVG aspect ratio (from viewBox)
                const vb = svgEl.viewBox.baseVal;
                const svgW = vb.width;
                const svgH = vb.height;
                
                // Set HTML attributes so wrapper takes correct shape
                svgEl.setAttribute('width', svgW);
                svgEl.setAttribute('height', svgH);

                const containerW = container.offsetWidth;
                const containerH = container.offsetHeight;
                
                const scaleX = containerW / svgW;
                const scaleY = containerH / svgH;
                
                // Pick optimal scale (fit fully inside) with 5% margin
                let optimalScale = Math.min(scaleX, scaleY) * 0.95;
                if(optimalScale < 0.1) optimalScale = 0.1; 
                
                currentZoom = optimalScale;
                updateZoomDisplay();
            }}

            // Main Auto Crop Function
            function autoCrop() {{
                try {{
                    setToBeContentBox();
                    zoomToFitContainer();
                    document.getElementById('status-text').innerText = "Auto Cropped";
                }} catch(e) {{
                    console.error("Auto Fit Failed", e);
                }}
            }}

            // Run on Load
            window.onload = function() {{
               setTimeout(autoCrop, 50);
            }};

            // --- MANUAL CROP APPLY ---
            function applyCrop() {{
                const metrics = getCropMetrics(); 
                
                // Update SVG viewBox to MANUAL selection
                svgEl.setAttribute('viewBox', `${{metrics.x}} ${{metrics.y}} ${{metrics.w}} ${{metrics.h}}`);
                
                // Resize wrapper to match new aspect
                svgEl.setAttribute('width', metrics.w);
                svgEl.setAttribute('height', metrics.h);
                
                toggleCropTool();
                
                // Zoom to fit the NEW selection into the viewer
                zoomToFitContainer();
                
                document.getElementById('status-text').innerText = "Manual Crop Applied";
            }}

            // --- PERSISTENCE ---
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
                                el.setAttribute('transform', `translate(${{pos.x}}, ${{pos.y}})`);
                            }} catch(e) {{}}
                        }}
                    }}
                }});
            }}

            function resetAll() {{
                Object.keys(sessionStorage).forEach(key => {{
                    if(key.startsWith(storageKeyPrefix)) sessionStorage.removeItem(key);
                }});
                document.querySelectorAll('.draggable-label').forEach(el => el.removeAttribute('transform'));
                
                // Restore Original ViewBox
                svgEl.setAttribute('viewBox', ORIG_VIEWBOX_STR);
                svgEl.removeAttribute('width');
                svgEl.removeAttribute('height');
                
                // Reset Zoom
                setTimeout(autoCrop, 50);
                
                cropModeActive = false;
                cropLayer.style.display = 'none';
                btnApplyCrop.style.display = 'none';
                btnCropTool.innerHTML = "✂️ Manual";
                btnCropTool.classList.remove('btn-red');
                btnCropTool.classList.add('btn-purple');
            }}

            // --- DRAG LABELS ---
            let dragTarget = null;
            let dragOffset = {{x:0, y:0}};
            let dragStartTransform = {{x:0, y:0}};

            function getTranslate(el) {{
                const transform = el.getAttribute('transform');
                if (!transform) return {{x: 0, y: 0}};
                const match = /translate\(([^,]+),([^)]+)\)/.exec(transform);
                if (match) return {{x: parseFloat(match[1]), y: parseFloat(match[2])}};
                return {{x: 0, y: 0}};
            }}

            svgEl.addEventListener('mousedown', (e) => {{
                if(cropModeActive) return; 
                const el = e.target.closest('.draggable-label');
                if (el) {{
                    dragTarget = el;
                    const CTM = svgEl.getScreenCTM();
                    dragOffset.x = (e.clientX - CTM.e) / CTM.a;
                    dragOffset.y = (e.clientY - CTM.f) / CTM.d;
                    dragStartTransform = getTranslate(dragTarget);
                    e.preventDefault();
                }}
            }});

            window.addEventListener('mousemove', (e) => {{
                if (dragTarget) {{
                    e.preventDefault();
                    const CTM = svgEl.getScreenCTM();
                    const dx = (e.clientX - CTM.e) / CTM.a - dragOffset.x;
                    const dy = (e.clientY - CTM.f) / CTM.d - dragOffset.y;
                    dragTarget.setAttribute('transform', `translate(${{dragStartTransform.x + dx}}, ${{dragStartTransform.y + dy}})`);
                }}
            }});

            window.addEventListener('mouseup', () => {{
                if (dragTarget) {{
                    const transform = getTranslate(dragTarget);
                    if (dragTarget.id) sessionStorage.setItem(storageKeyPrefix + dragTarget.id, JSON.stringify(transform));
                    dragTarget = null;
                }}
            }});

            restorePositions();

            // --- CROP TOOL ---
            let isResizingCrop = false;
            let isMovingCrop = false;
            let cropStart = {{x:0, y:0, w:0, h:0, mx:0, my:0}};
            let activeHandle = null;

            function toggleCropTool() {{
                cropModeActive = !cropModeActive;
                
                if (cropModeActive) {{
                    cropLayer.style.display = 'block';
                    btnApplyCrop.style.display = 'inline-flex';
                    btnCropTool.innerHTML = "❌ Cancel";
                    btnCropTool.classList.remove('btn-purple');
                    btnCropTool.classList.add('btn-red');
                    
                    // Smart Init: Snap to content BBox, converted to current zoom/view space
                    try {{
                        const bbox = svgEl.getBBox();
                        const vb = svgEl.viewBox.baseVal;
                        
                        // Get current pixel size of SVG
                        const style = window.getComputedStyle(svgEl);
                        const w_px = parseFloat(style.width);
                        const h_px = parseFloat(style.height);

                        // Scale factor (Pixels per SVG unit)
                        const scaleX = w_px / vb.width;
                        const scaleY = h_px / vb.height;

                        const pad = 10;
                        
                        // Convert SVG coords to CSS pixels relative to top-left of SVG element
                        const bx = (bbox.x - vb.x - pad) * scaleX;
                        const by = (bbox.y - vb.y - pad) * scaleY;
                        const bw = (bbox.width + pad*2) * scaleX;
                        const bh = (bbox.height + pad*2) * scaleY;

                        setCropBox(bx, by, bw, bh);
                    }} catch(e) {{
                        const rect = svgEl.getBoundingClientRect();
                        setCropBox(10, 10, rect.width-20, rect.height-20);
                    }}
                    
                }} else {{
                    cropLayer.style.display = 'none';
                    btnApplyCrop.style.display = 'none';
                    btnCropTool.innerHTML = "✂️ Manual";
                    btnCropTool.classList.remove('btn-red');
                    btnCropTool.classList.add('btn-purple');
                }}
            }}

            function setCropBox(x, y, w, h) {{
                cropBox.style.left = x + 'px';
                cropBox.style.top = y + 'px';
                cropBox.style.width = w + 'px';
                cropBox.style.height = h + 'px';
            }}

            cropBox.addEventListener('mousedown', (e) => {{
                if (e.target.classList.contains('resize-handle')) {{
                    isResizingCrop = true;
                    activeHandle = e.target.dataset.dir;
                }} else {{
                    isMovingCrop = true;
                }}
                
                cropStart = {{
                    x: parseFloat(cropBox.style.left),
                    y: parseFloat(cropBox.style.top),
                    w: parseFloat(cropBox.style.width),
                    h: parseFloat(cropBox.style.height),
                    mx: e.clientX,
                    my: e.clientY
                }};
                e.stopPropagation(); 
            }});

            window.addEventListener('mousemove', (e) => {{
                if (!cropModeActive) return;

                const dx = (e.clientX - cropStart.mx) / currentZoom;
                const dy = (e.clientY - cropStart.my) / currentZoom;

                if (isMovingCrop) {{
                    setCropBox(cropStart.x + dx, cropStart.y + dy, cropStart.w, cropStart.h);
                }} else if (isResizingCrop) {{
                    let nx=cropStart.x, ny=cropStart.y, nw=cropStart.w, nh=cropStart.h;

                    if (activeHandle.includes('e')) nw = cropStart.w + dx;
                    if (activeHandle.includes('s')) nh = cropStart.h + dy;
                    if (activeHandle.includes('w')) {{ nx = cropStart.x + dx; nw = cropStart.w - dx; }}
                    if (activeHandle.includes('n')) {{ ny = cropStart.y + dy; nh = cropStart.h - dy; }}

                    if(nw > 20 && nh > 20) setCropBox(nx, ny, nw, nh);
                }}
            }});

            window.addEventListener('mouseup', () => {{
                isMovingCrop = false;
                isResizingCrop = false;
            }});

            function getCropMetrics() {{
                const rect = svgEl.getBoundingClientRect(); 
                const vb = svgEl.viewBox.baseVal; 
                
                const scaleX = vb.width / rect.width;
                const scaleY = vb.height / rect.height;

                const cropRect = cropBox.getBoundingClientRect();
                
                const pxLeft = cropRect.left - rect.left;
                const pxTop = cropRect.top - rect.top;
                
                const svgX = vb.x + (pxLeft * scaleX);
                const svgY = vb.y + (pxTop * scaleY);
                const svgW = cropRect.width * scaleX;
                const svgH = cropRect.height * scaleY;

                return {{ x: svgX, y: svgY, w: svgW, h: svgH }};
            }}

            function downloadSVG() {{
                const clone = svgEl.cloneNode(true);
                if(cropModeActive) {{
                     const metrics = getCropMetrics();
                     clone.setAttribute('viewBox', `${{metrics.x}} ${{metrics.y}} ${{metrics.w}} ${{metrics.h}}`);
                }}
                
                const vb = clone.viewBox.baseVal;
                const ratio = vb.width / vb.height;
                const newHeightCm = TARGET_W_CM / ratio; 
                
                clone.setAttribute('width', TARGET_W_CM + 'cm');
                clone.setAttribute('height', newHeightCm + 'cm');

                const svgData = new XMLSerializer().serializeToString(clone);
                const blob = new Blob([svgData], {{type: "image/svg+xml;charset=utf-8"}});
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'graph.svg';
                link.click();
            }}

            function downloadPNG() {{
                const clone = svgEl.cloneNode(true);
                if(cropModeActive) {{
                     const metrics = getCropMetrics();
                     clone.setAttribute('viewBox', `${{metrics.x}} ${{metrics.y}} ${{metrics.w}} ${{metrics.h}}`);
                }}
                
                const vb = clone.viewBox.baseVal;
                const scaleFactor = 10; 
                const w = vb.width * scaleFactor;
                const h = vb.height * scaleFactor;
                
                clone.setAttribute('width', w);
                clone.setAttribute('height', h);

                const svgData = new XMLSerializer().serializeToString(clone);
                const img = new Image();
                img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgData)));

                img.onload = function() {{
                    const canvas = document.createElement("canvas");
                    canvas.width = w; 
                    canvas.height = h;
                    const ctx = canvas.getContext("2d");
                    ctx.fillStyle = "white";
                    ctx.fillRect(0, 0, w, h);
                    ctx.drawImage(img, 0, 0, w, h);
                    
                    const link = document.createElement('a');
                    link.download = 'graph.png';
                    link.href = canvas.toDataURL("image/png");
                    link.click();
                }};
            }}

        </script>
    </body>
    </html>
    """

    components.html(html_code, height=900, scrolling=True)