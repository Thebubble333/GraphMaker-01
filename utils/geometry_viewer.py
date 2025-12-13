import streamlit.components.v1 as components
import json
import os

def render_geometry_editor(shapes_data, width_px, height_px, canvas_width_cm, canvas_height_cm):
    """
    Renders the interactive JS Geometry Editor.
    shapes_data: List of dicts describing shapes (id, type, points: [{'x':, 'y':}], color, etc.)
    """
    
    shapes_json = json.dumps(shapes_data)
    
    # Load JS
    js_path = os.path.join(os.path.dirname(__file__), 'geometry_logic.js')
    try:
        with open(js_path, "r") as f:
            js_logic = f.read()
    except FileNotFoundError:
        js_logic = "console.error('Error: geometry_logic.js not found in utils folder');"

    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ margin: 0; padding: 0; background: #f0f2f6; font-family: sans-serif; }}
            .container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 10px;
            }}
            #geo-canvas {{ 
                background: white; 
                box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
                border: 1px solid #ddd;
                cursor: default;
                display: block;
            }}
            .info-bar {{
                margin-bottom: 10px;
                padding: 8px 15px;
                background: #fff;
                border-radius: 4px;
                font-size: 14px;
                color: #555;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="info-bar">
                <b>Beta Mode:</b> Drag shapes (body) or vertices (dots). 
                <i>Changes here do not sync back to sliders.</i>
            </div>
            <svg id="geo-canvas" width="{width_px}" height="{height_px}" viewBox="0 0 {width_px} {height_px}"></svg>
        </div>
        
        <script>
            // Data Injection
            const SHAPES = {shapes_json};
            const TARGET_W_CM = {canvas_width_cm};
            const TARGET_H_CM = {canvas_height_cm};
            
            // Logic Injection
            {js_logic}
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=height_px + 100, scrolling=True)