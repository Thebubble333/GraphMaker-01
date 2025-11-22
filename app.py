import streamlit as st
import base64
import math
import streamlit.components.v1 as components
from graph_maker import GraphEngine, GraphConfig

# 1. Layout "wide" allows us to use columns effectively
st.set_page_config(layout="wide", page_title="GraphMaker")

# --- CSS HACKS FOR COMPACT UI ---
st.markdown("""
    <style>
        /* Fix top clipping by giving more room */
        .block-container {
            padding-top: 4rem; 
            padding-bottom: 1rem;
        }
        h1 {
            margin-top: 0rem;
            font-size: 1.8rem; /* Smaller title */
        }

        /* Tweak expander to look cleaner */
        .streamlit-expanderHeader {
            font-size: 0.9rem;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

# --- Constants & Helpers ---
NAME_TO_HEX = {
    "blue": "#0000FF",
    "red": "#FF0000",
    "green": "#008000",
    "purple": "#800080",
    "orange": "#FFA500",
    "black": "#000000"
}


def render_png_button(svg_string, width, height, scale_factor):
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <div id="svg-source" style="display:none;">{svg_string}</div>
        <button id="btn-download" style="background-color: #4CAF50; border: none; color: white; padding: 6px 12px; text-align: center; text-decoration: none; display: inline-block; font-size: 12px; margin: 0px; cursor: pointer; border-radius: 4px; font-family: sans-serif;">
            Download PNG
        </button>
        <script>
            document.getElementById("btn-download").onclick = function() {{
                var svgElement = document.getElementById("svg-source").querySelector("svg");
                svgElement.setAttribute("width", "{width}px");
                svgElement.setAttribute("height", "{height}px");
                var svgData = new XMLSerializer().serializeToString(svgElement);
                var img = new Image();
                img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgData)));
                img.onload = function() {{
                    var canvas = document.createElement("canvas");
                    var scale = {scale_factor};
                    canvas.width = {width} * scale;
                    canvas.height = {height} * scale;
                    var ctx = canvas.getContext("2d");
                    ctx.scale(scale, scale);
                    ctx.fillStyle = "white";
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0, {width}, {height});
                    var link = document.createElement('a');
                    link.download = 'graph_high_res.png';
                    link.href = canvas.toDataURL("image/png");
                    link.click();
                }};
            }};
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=35)


def calculate_auto_scale_physical(val_min, val_max, size_cm):
    span = val_max - val_min
    if span <= 0: return 1.0
    target_tick_spacing_cm = 2.0
    approx_num_ticks = size_cm / target_tick_spacing_cm
    if approx_num_ticks < 1: approx_num_ticks = 1
    raw_step = span / approx_num_ticks
    power = 10 ** math.floor(math.log10(raw_step))
    base = raw_step / power
    if base < 1.5:
        step = 1.0 * power
    elif base < 3.5:
        step = 2.0 * power
    elif base < 7.5:
        step = 5.0 * power
    else:
        step = 10.0 * power
    return max(step, 0.1)


# --- Sidebar ---
st.sidebar.title("📐 GraphMaker")
st.sidebar.header("Grid Settings")

mode = st.sidebar.radio("Input Mode", ["Min/Max Window", "Range & Center"], horizontal=True)

# Defaults
scale_x = 1.0
scale_y = 1.0
minor_spacing_x = 10.0
minor_spacing_y = 10.0
target_width_cm = 12.0
target_height_cm = 12.0

if mode == "Min/Max Window":
    st.sidebar.markdown("### Window Limits")
    link_xy = st.sidebar.checkbox("Link X/Y Scale", value=False)
    auto_scale = st.sidebar.checkbox("Auto-pick Grid Scale", value=True)

    st.sidebar.markdown("### Target Print Size (cm)")
    c_dim1, c_dim2 = st.sidebar.columns(2)
    target_width_cm = c_dim1.number_input("Width (cm)", 5.0, 50.0, 12.0, step=0.5)
    target_height_cm = c_dim2.number_input("Height (cm)", 5.0, 50.0, 12.0, step=0.5)

    target_width_pts = target_width_cm * 28.3465
    target_height_pts = target_height_cm * 28.3465

    st.sidebar.markdown("### Axes")
    c_x1, c_x2 = st.sidebar.columns(2)
    xmin = c_x1.number_input("X Min", value=-10.0, step=1.0)
    xmax = c_x2.number_input("X Max", value=10.0, step=1.0)

    c_y1, c_y2 = st.sidebar.columns(2)
    ymin = c_y1.number_input("Y Min", value=-10.0, step=1.0)
    ymax = c_y2.number_input("Y Max", value=10.0, step=1.0)

    width_units = xmax - xmin
    height_units = ymax - ymin

    if auto_scale:
        scale_x = calculate_auto_scale_physical(xmin, xmax, target_width_cm)
        if link_xy:
            scale_y = scale_x
        else:
            scale_y = calculate_auto_scale_physical(ymin, ymax, target_height_cm)
    else:
        if link_xy:
            scale_x = st.sidebar.number_input("Grid Scale", 0.1, 100.0, 1.0)
            scale_y = scale_x
        else:
            c_s1, c_s2 = st.sidebar.columns(2)
            scale_x = c_s1.number_input("X Scale", 0.1, 100.0, 1.0)
            scale_y = c_s2.number_input("Y Scale", 0.1, 100.0, 1.0)

    x_cols = max(1, math.ceil(width_units / scale_x))
    y_cols = max(1, math.ceil(height_units / scale_y))

    axis_x_pos_calc = abs(xmin) / scale_x if xmin <= 0 <= xmax else 0
    axis_y_pos_calc = abs(ymin) / scale_y if ymin <= 0 <= ymax else 0

    axis_x_pos = int(round(axis_x_pos_calc))
    axis_y_pos = int(round(axis_y_pos_calc))

    if x_cols > 0: minor_spacing_x = target_width_pts / (x_cols * 5)
    if y_cols > 0: minor_spacing_y = target_height_pts / (y_cols * 5)

    x_range = x_cols
    y_range = y_cols

else:  # Range & Center Mode
    c1, c2 = st.sidebar.columns(2)
    x_range = c1.slider("X Axis Range (Total Units)", 5, 50, 10)
    y_range = c2.slider("Y Axis Range (Total Units)", 5, 50, 10)

    link_xy = st.sidebar.checkbox("Link X/Y Scale", value=True)
    if link_xy:
        scale_x = st.sidebar.number_input("Grid Scale (Units per tick)", 0.1, 10.0, 1.0)
        scale_y = scale_x
    else:
        c_s1, c_s2 = st.sidebar.columns(2)
        scale_x = c_s1.number_input("X Scale", 0.1, 10.0, 1.0)
        scale_y = c_s2.number_input("Y Scale", 0.1, 10.0, 1.0)

    c3, c4 = st.sidebar.columns(2)
    axis_x_pos = c3.slider("Y-Axis Position (from left)", 0, x_range, int(x_range / 2))
    axis_y_pos = c4.slider("X-Axis Position (from bottom)", 0, y_range, int(y_range / 2))

st.sidebar.markdown("### Axis Customization")
c_tog1, c_tog2 = st.sidebar.columns(2)
show_minor = c_tog1.checkbox("Minor Grid", value=True)
show_major = c_tog2.checkbox("Major Grid", value=True)
show_x_axis = c_tog1.checkbox("X Axis Line", value=True)
show_y_axis = c_tog2.checkbox("Y Axis Line", value=True)

c_tick1, c_tick2 = st.sidebar.columns(2)
show_x_ticks = c_tick1.checkbox("X Axis Ticks", value=True)
show_y_ticks = c_tick2.checkbox("Y Axis Ticks", value=True)

c_num1, c_num2 = st.sidebar.columns(2)
show_x_nums = c_num1.checkbox("X Axis Scale", value=True)
show_y_nums = c_num2.checkbox("Y Axis Scale", value=True)

c5, c6 = st.sidebar.columns(2)
label_x = c5.text_input("X Label", "x")
label_y = c6.text_input("Y Label", "y")

with st.sidebar.expander("Advanced Settings"):
    log_step = st.slider("Step Size (Log Scale)", -4.0, -1.0, -1.0)
    step_size = math.pow(10, log_step)
    st.write(f"Current Step Size: `{step_size:.5f}`")
    font_size_override = st.slider("Font Size (pt)", 8, 24, 11)

# --- Main Layout ---
col_funcs, col_preview = st.columns([2, 3])

# --- Init Session State ---
if 'funcs_data' not in st.session_state:
    st.session_state.funcs_data = [
        {'expr': "sin(x)", 'color': "#000000", 'thick': 1.5, 'label': False},
        {'expr': "x^2/10 - 2", 'color': "#FF0000", 'thick': 1.5, 'label': False}
    ]


def add_func():
    st.session_state.funcs_data.append({'expr': "", 'color': "#000000", 'thick': 1.5, 'label': False})


def remove_func(idx):
    st.session_state.funcs_data.pop(idx)


# --- LEFT COLUMN: Functions ---
with col_funcs:
    st.subheader("Functions")

    for i, func_obj in enumerate(st.session_state.funcs_data):
        with st.expander(f"Function {i + 1}", expanded=True):
            c_expr, c_del = st.columns([5, 1])
            func_obj['expr'] = c_expr.text_input("Expr", func_obj['expr'], key=f"expr_{i}",
                                                 label_visibility="collapsed", placeholder="e.g. sin(x)")
            if c_del.button("🗑️", key=f"del_{i}"):
                remove_func(i)
                st.rerun()

            c_col, c_thk, c_lbl = st.columns([1, 2, 2])

            current_col = func_obj['color']
            if not current_col.startswith('#'):
                current_col = NAME_TO_HEX.get(current_col, "#000000")

            func_obj['color'] = c_col.color_picker("C", current_col, key=f"col_{i}", label_visibility="collapsed")
            func_obj['thick'] = c_thk.number_input("Thick", 0.5, 10.0, func_obj['thick'], step=0.5, key=f"thk_{i}",
                                                   label_visibility="collapsed")
            func_obj['label'] = c_lbl.checkbox("Label", func_obj['label'], key=f"lbl_{i}")

    if st.button("➕ Function"):
        add_func()
        st.rerun()

# --- RIGHT COLUMN: Preview & Export ---
with col_preview:
    # Generate Graph first
    config = GraphConfig(
        grid_cols=(x_range, y_range),
        grid_scale=(scale_x, scale_y),
        axis_pos=(axis_y_pos, axis_x_pos),
        axis_labels=(label_x, label_y),
        tick_rounding=(1, 1),
        minor_spacing=(minor_spacing_x, minor_spacing_y),
        font_size=font_size_override,
        show_minor_grid=show_minor,
        show_major_grid=show_major,
        show_x_axis=show_x_axis,
        show_y_axis=show_y_axis,
        show_x_numbers=show_x_nums,
        show_y_numbers=show_y_nums,
        show_x_ticks=show_x_ticks,
        show_y_ticks=show_y_ticks
    )

    engine = GraphEngine(config)
    engine.draw_grid_lines()
    engine.draw_axis_labels()

    for func_obj in st.session_state.funcs_data:
        if func_obj['expr'].strip():
            lbl = func_obj['expr'] if func_obj['label'] else None
            engine.plot_function(
                func_obj['expr'],
                color=func_obj['color'],
                base_step=step_size,
                line_thickness=func_obj['thick'],
                label_text=lbl
            )

    svg_string = engine.get_svg_string()

    # Top Control Row
    c_head, c_scale, c_png, c_svg = st.columns([2, 2, 2, 2])

    with c_head:
        st.subheader("Preview")
    with c_scale:
        scale_choice = st.number_input("PNG Scale", 1, 10, 4, label_visibility="collapsed")
    with c_png:
        render_png_button(svg_string, engine.width_pixels, engine.height_pixels, scale_choice)
    with c_svg:
        svg_physical = svg_string.replace('width="100%"', f'width="{target_width_cm:.2f}cm"')
        svg_physical = svg_physical.replace('height="100%"', f'height="{target_height_cm:.2f}cm"')
        b64 = base64.b64encode(svg_physical.encode('utf-8')).decode("utf-8")
        href = f'<a href="data:image/svg+xml;base64,{b64}" download="graph.svg" style="background-color: #eee; border: 1px solid #ccc; color: #333; padding: 6px 12px; text-decoration: none; display: inline-block; font-size: 12px; margin-top: 0px; border-radius: 4px; font-family: sans-serif;">Download SVG</a>'
        st.markdown(href, unsafe_allow_html=True)

    # The Graph - Vertically Constrained
    # Uses max-height: 75vh to ensure it fits on screen without scrolling
    # Uses display: flex to center the image if it shrinks
    st.markdown(f"""
        <div style="
            background-color: white; 
            padding: 5px; 
            border-radius: 5px; 
            width: 100%; 
            height: 100%;
            max-height: 75vh;
            display: flex; 
            justify-content: center; 
            align-items: flex-start; 
            margin: 0 auto; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: auto;
        ">
            {svg_string.replace('<svg ', '<svg style="max-height: 75vh; width: auto; max-width: 100%;" ')}
        </div>
        """, unsafe_allow_html=True)