import streamlit as st
import math
import sys
import os
import re

# Add parent directory to path so we can import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Switch to StatsGraphEngine to support marker_type (hollow circles)
# CORRECTED IMPORT: Import GraphConfig from graph_base to ensure all attributes (like force_external_margins) exist
from utils.graph_base import GraphConfig
from utils.graph_stats import StatsGraphEngine
from utils.interactive_viewer import render_interactive_graph
from utils.nav import render_sidebar

st.set_page_config(layout="wide", page_title="Number Line")
render_sidebar()

# --- CSS Tweaks ---
st.markdown("""
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 3rem !important; padding-bottom: 1rem; } 
        [data-testid="stSidebarUserContent"] { padding-top: 1.5rem; }
        [data-testid="stSidebar"] hr { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; }
        [data-testid="stSidebar"] h1 { padding-top: 0rem !important; margin-top: 0rem !important; font-size: 1.8rem; }
        [data-testid="stSidebar"] .stElementContainer { margin-bottom: 0.5rem; }
        div[data-testid="column"] { padding: 0px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: Settings ---
st.sidebar.title("➖ Settings")

st.sidebar.markdown("### Target Print Size")
target_width_cm = st.sidebar.number_input("Width (cm)", 5.0, 50.0, 12.0, step=0.5)
target_height_cm = st.sidebar.number_input("Height (cm)", 2.0, 50.0, 4.0, step=0.5)
target_width_pts = target_width_cm * 28.3465
target_height_pts = target_height_cm * 28.3465

st.sidebar.markdown("### Axis Range")
# Initialize session state for window
if 'nl_xmin' not in st.session_state:
    st.session_state.nl_xmin = -10.0
    st.session_state.nl_xmax = 10.0
    st.session_state.nl_scale = 1.0

c1, c2 = st.sidebar.columns(2)
x_min = c1.number_input("Min", -1000.0, 1000.0, st.session_state.nl_xmin, step=1.0)
x_max = c2.number_input("Max", -1000.0, 1000.0, st.session_state.nl_xmax, step=1.0)
scale_x = st.sidebar.number_input("Grid Scale", 0.1, 5000.0, st.session_state.nl_scale)
label_x = st.sidebar.text_input("Axis Label", "x")

with st.sidebar.expander("Advanced Calibration"):
    # show_minor = st.checkbox("Show Minor Gridlines", value=True) # REMOVED per user request
    # show_major = st.checkbox("Show Major Gridlines", value=True) # REMOVED per user request
    minor_subs = st.slider("Minor Subdivisions", 1, 10, 2)
    off_set_lbl = st.slider("Set Label Offset Y", -50.0, 50.0, 0.0, step=1.0)
    off_x_num = st.slider("Axis Numbers Y", -50.0, 50.0, -5.0, step=1.0)
    off_x_lbl = st.slider("Axis Label Y", -50.0, 50.0, -15.0, step=1.0)

# --- MAIN LAYOUT ---
col_data, col_preview = st.columns([2, 3])


# --- HELPER: PARSER ---
def parse_interval_latex(latex_str):
    """
    Parses LaTeX interval notation like (-\infty, 3) \cup [4, 5).
    Returns a list of dicts: {'start': float, 'end': float, 'start_type': 'open'/'closed', 'end_type': 'open'/'closed'}
    """
    # Remove \cup and whitespace
    clean_str = latex_str.replace(r'\cup', ' ').replace(r'\union', ' ')

    # Regex for intervals: matches ( or [, start, comma, end, ) or ]
    # Handles numbers, \infty, -\infty, inf, -inf
    # Group 1: Open/Close Start
    # Group 2: Start Value
    # Group 3: End Value
    # Group 4: Open/Close End
    pattern = r'(\[|\()\s*(-?\\infty|[-\d\.]+|inf|-inf)\s*,\s*(-?\\infty|[-\d\.]+|inf|-inf)\s*(\]|\))'

    matches = re.findall(pattern, clean_str)
    intervals = []

    for open_b, start_s, end_s, close_b in matches:
        # Parse Start
        if 'infty' in start_s or 'inf' in start_s:
            s_val = float('-inf') if '-' in start_s else float('inf')
        else:
            try:
                s_val = float(start_s)
            except:
                continue

        # Parse End
        if 'infty' in end_s or 'inf' in end_s:
            e_val = float('-inf') if '-' in end_s else float('inf')
        else:
            try:
                e_val = float(end_s)
            except:
                continue

        intervals.append({
            'start': s_val,
            'end': e_val,
            'start_type': 'closed' if open_b == '[' else 'open',
            'end_type': 'closed' if close_b == ']' else 'open'
        })

    return intervals


# --- HELPER: DRAW ARROW ---
def draw_arrow_head(engine, x, y, direction, color, size=10):
    """Draws a triangle arrow head at math coordinates (x, y)"""
    px, py = engine.math_to_screen(x, y)

    # Triangle points
    # Sharp arrow: length 12, width 8 (half width 4)
    length = size * 1.2
    half_width = size * 0.4

    if direction == 'left':
        # Pointing left: Tip at (px, py), Base at (px + length)
        points = [
            (px, py),
            (px + length, py - half_width),
            (px + length, py + half_width)
        ]
    elif direction == 'right':
        # Pointing right: Tip at (px, py), Base at (px - length)
        points = [
            (px, py),
            (px - length, py - half_width),
            (px - length, py + half_width)
        ]
    else:
        return

    engine.dwg.add(engine.dwg.polygon(points=points, fill=color, stroke="none"))

    return length  # Return length in pixels to adjust line end


# --- LEFT COLUMN: Data Entry ---
with col_data:
    st.subheader("Interval Sets")

    if 'num_nl_sets' not in st.session_state:
        st.session_state.num_nl_sets = 1


    def add_set():
        st.session_state.num_nl_sets += 1


    def remove_set():
        if st.session_state.num_nl_sets > 1:
            st.session_state.num_nl_sets -= 1


    sets_data = []

    for i in range(st.session_state.num_nl_sets):
        with st.expander(f"Set {i + 1}", expanded=True):
            # Default example
            def_val = r"(-\infty, -2) \cup [1, 4)" if i == 0 else "[2, 5]"

            c_lbl, c_expr = st.columns([1, 3])
            lbl = c_lbl.text_input("Label", f"", key=f"lbl_{i}", placeholder="Optional")
            expr = c_expr.text_area("Interval (LaTeX)", def_val, height=70, key=f"expr_{i}")

            c_style1, c_style2, c_style3 = st.columns(3)
            color = c_style1.color_picker("Color", "#000000" if i == 0 else "#FF0000", key=f"col_{i}")
            thick = c_style2.number_input("Thickness", 0.5, 5.0, 1.5, step=0.25, key=f"thk_{i}")
            y_offset = c_style3.number_input("Vertical Pos", 1, 10, i + 1, key=f"ypos_{i}",
                                             help="Vertical stacking order")

            parsed = parse_interval_latex(expr)
            sets_data.append({
                'label': lbl,
                'intervals': parsed,
                'color': color,
                'thick': thick,
                'y_level': float(y_offset)
            })

    c_add, c_rem = st.columns([1, 1])
    c_add.button("➕ Add Set", on_click=add_set, use_container_width=True)
    c_rem.button("➖ Remove", on_click=remove_set, use_container_width=True,
                 disabled=(st.session_state.num_nl_sets <= 1))

    st.info(r"Supported inputs: `(-\infty, 3)`, `[2, 5)`, `[-2, 2] \cup (4, \infty)`")

# --- RIGHT COLUMN: Preview ---
with col_preview:
    st.subheader("Preview")

    # 1. Calculate Grid
    width_units = x_max - x_min
    if width_units <= 0: width_units = 1.0

    # Determine Y range based on sets (add padding)
    max_y_level = max([s['y_level'] for s in sets_data]) if sets_data else 1.0
    y_max_graph = max_y_level + 1.0
    y_min_graph = 0.0  # Axis is at 0
    height_units = y_max_graph - y_min_graph

    # Auto-calc rows/cols
    num_major_x = math.ceil(width_units / scale_x)
    if num_major_x < 1: num_major_x = 1

    # We want a fixed Y scale of 1.0 usually for number lines
    scale_y = 1.0
    num_major_y = math.ceil(height_units / scale_y)

    pixels_per_unit_x = target_width_pts / width_units
    minor_spacing_x = (pixels_per_unit_x * scale_x) / (
        5 if minor_subs == 0 else minor_subs * 5)  # Rough heuristic fallback

    # Recalculate exact minor spacing
    if num_major_x > 0 and minor_subs > 0:
        minor_spacing_x = target_width_pts / (num_major_x * minor_subs)

    # Config
    config = GraphConfig(
        grid_cols=(int(num_major_x), int(num_major_y)),
        grid_scale=(scale_x, scale_y),
        # Fix Axis Pos: Y-axis is at column index matching x=0, X-axis is at BOTTOM (max row index)
        axis_pos=(int(num_major_y), int(-x_min / scale_x)),
        axis_labels=(label_x, ""),
        minor_spacing=(minor_spacing_x, 20.0),  # Y spacing irrelevant if hidden
        minor_per_major=(minor_subs, 1),  # Sync minor subs with GraphBase logic

        # GRID LOGIC:
        # We want ticks (requires show_vertical_grid=True)
        # But we don't want lines (requires show_major_grid=False, show_minor_grid=False)
        show_vertical_grid=True,
        show_major_grid=False,
        show_minor_grid=False,

        show_horizontal_grid=False,  # No horiz grid for number lines usually
        show_y_axis=False,  # Explicitly requested NO Y AXIS
        show_x_axis=True,
        show_x_numbers=True,
        show_y_numbers=False,
        show_x_ticks=True,
        show_y_ticks=False,
        show_border=False,  # Open look

        offset_xaxis_num_y=off_x_num,
        offset_xaxis_label_y=off_x_lbl,
    )

    # Use StatsGraphEngine for marker support
    engine = StatsGraphEngine(config)
    engine.draw_grid_lines()
    engine.draw_axis_labels()

    # --- MANUAL FIX: Draw Tick at 0 ---
    # The engine skips drawing the tick at the axis crossing to avoid clutter.
    # Since we hid the Y-axis, we need to put that tick back manually.
    if x_min <= 0 <= x_max:
        px_0, py_0 = engine.math_to_screen(0, 0)
        # origin_y corresponds to the X-axis line Y position
        # Standard tick is +/- 7px from axis
        tick_h = 7
        engine.dwg.add(engine.dwg.line(
            start=(px_0, engine.origin_y - tick_h),
            end=(px_0, engine.origin_y + tick_h),
            stroke='black', stroke_width=config.axis_thickness
        ))

    # Draw Sets
    for data in sets_data:
        y = data['y_level']
        c = data['color']
        thk = data['thick']

        # 1. Collect Endpoints to draw later (so they are on top of lines)
        closed_points_x = []
        closed_points_y = []
        open_points_x = []
        open_points_y = []

        for interval in data['intervals']:
            start = interval['start']
            end = interval['end']

            # Handle Infinity for Drawing Lines
            is_start_infinite = math.isinf(start)
            is_end_infinite = math.isinf(end)

            # Setup drawing coordinates
            draw_start = start
            draw_end = end

            # Helper to convert pixel length to graph units
            # We need this to stop the line *before* the arrowhead
            px_per_unit = config.pixels_per_unit_x

            # Clamp and Add Arrows
            if is_start_infinite:
                # Clamp to graph edge
                draw_start = x_min
                # Draw Arrow at edge pointing left
                arrow_px = draw_arrow_head(engine, draw_start, y, 'left', c)
                # Offset line start by arrow length (in graph units)
                arrow_units = arrow_px / px_per_unit
                draw_start += arrow_units

            if is_end_infinite:
                # Clamp to graph edge
                draw_end = x_max
                # Draw Arrow at edge pointing right
                arrow_px = draw_arrow_head(engine, draw_end, y, 'right', c)
                # Offset line end by arrow length (in graph units)
                arrow_units = arrow_px / px_per_unit
                draw_end -= arrow_units

            # Clip visual range for line safety (in case non-infinite values are outside view)
            # We do this AFTER arrow calculation so the arrow stays at the edge
            draw_start = max(draw_start, x_min)
            draw_end = min(draw_end, x_max)

            # Draw the Line Segment
            if draw_end > draw_start:
                engine.draw_scatter(
                    [draw_start, draw_end],
                    [y, y],
                    connect=True,
                    color=c,
                    marker_type="None",
                    marker_size=0,
                )

            # Collect Endpoints (Only if finite)
            if not is_start_infinite:
                if x_min <= start <= x_max:
                    if interval['start_type'] == 'closed':
                        closed_points_x.append(start)
                        closed_points_y.append(y)
                    else:
                        open_points_x.append(start)
                        open_points_y.append(y)

            if not is_end_infinite:
                if x_min <= end <= x_max:
                    if interval['end_type'] == 'closed':
                        closed_points_x.append(end)
                        closed_points_y.append(y)
                    else:
                        open_points_x.append(end)
                        open_points_y.append(y)

        # 2. Draw Endpoints
        if closed_points_x:
            engine.draw_scatter(
                closed_points_x, closed_points_y,
                marker_type="circle",
                marker_size=3.5,
                color=c,
                connect=False
            )

        if open_points_x:
            engine.draw_scatter(
                open_points_x, open_points_y,
                marker_type="hollow_circle",
                marker_size=3.5,
                color=c,
                connect=False
            )

    svg_string = engine.get_svg_string()
    render_interactive_graph(svg_string, engine.width_pixels, engine.height_pixels, target_width_cm, target_height_cm,
                             10)