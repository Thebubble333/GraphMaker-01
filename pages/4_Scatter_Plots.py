import streamlit as st
import math
import sys
import os
import numpy as np

# Add parent directory to path so we can import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.graph_base import GraphConfig
from utils.graph_stats import StatsGraphEngine
from utils.interactive_viewer import render_interactive_graph
from utils.nav import render_sidebar

st.set_page_config(layout="wide", page_title="Scatter Plots")
render_sidebar()

# --- CSS Tweaks ---
st.markdown("""
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 2rem !important; padding-bottom: 1rem; } 
        div[data-testid="column"] { padding: 0px; }
        .stTextArea textarea { font-family: monospace; }
        /* Vertical alignment for side-by-side widgets */
        div.stSelectbox > label { display: none; } 
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SIDEBAR: GLOBAL CONFIG
# ==========================================
st.sidebar.title("⚙️ Calibration")

# --- Dimensions ---
st.sidebar.markdown("### Dimensions")
target_width_cm = st.sidebar.number_input("Target Width (cm)", 5.0, 50.0, 12.0, step=0.5)
target_height_cm = st.sidebar.number_input("Target Height (cm)", 5.0, 50.0, 10.0, step=0.5)

target_width_pts = target_width_cm * 28.3465
target_height_pts = target_height_cm * 28.3465

# ==========================================
# LAYOUT
# ==========================================
col_data, col_preview = st.columns([1.3, 1.7])

# ==========================================
# MAIN COLUMN 1: DATASETS
# ==========================================
with col_data:
    st.subheader("Data Input")

    # --- Plot Mode Toggle ---
    plot_mode = st.radio("Display Mode", ["Standard Scatter", "Residual Plot"], horizontal=True)
    is_residual = (plot_mode == "Residual Plot")

    if 'dataset_count' not in st.session_state:
        st.session_state.dataset_count = 1


    def add_dataset():
        st.session_state.dataset_count += 1


    def remove_dataset():
        if st.session_state.dataset_count > 1:
            st.session_state.dataset_count -= 1


    c_btn1, c_btn2 = st.columns(2)
    c_btn1.button("Add Dataset", on_click=add_dataset, use_container_width=True)
    c_btn2.button("Remove Last", on_click=remove_dataset, use_container_width=True,
                  disabled=(st.session_state.dataset_count <= 1))

    datasets_to_plot = []

    # Track globals for auto-scaling
    global_x_min = float('inf')
    global_x_max = float('-inf')
    global_y_min = float('inf')
    global_y_max = float('-inf')
    has_data = False

    # 1. Collect Raw Data
    for i in range(st.session_state.dataset_count):
        with st.expander(f"Dataset {i + 1}", expanded=(i == 0)):
            c_x, c_y = st.columns(2)
            x_str = c_x.text_area(f"X Values", "1, 2, 3, 4, 5" if i == 0 else "", height=100, key=f"x_{i}")
            y_str = c_y.text_area(f"Y Values", "2, 4, 6, 5, 8" if i == 0 else "", height=100, key=f"y_{i}")

            c_style1, c_style2, c_style3 = st.columns(3)
            marker_type = c_style1.selectbox("Marker", ["circle", "hollow_circle", "square", "cross", "plus"],
                                             key=f"m_type_{i}")
            marker_size = c_style2.number_input("Size", 1.0, 10.0, 3.5, step=0.5, key=f"m_size_{i}")
            marker_color = c_style3.color_picker("Color", "#000000" if i == 0 else "#FF0000", key=f"m_col_{i}")

            connect_pts = st.checkbox("Connect Points", value=False, key=f"conn_{i}")

            st.markdown("**Line of Best Fit**")
            c_lob1, c_lob2 = st.columns(2)
            show_reg = c_lob1.checkbox("Show Line", value=False, key=f"reg_{i}")
            lob_style = c_lob2.selectbox("Style", ["solid", "dotted"], key=f"lob_st_{i}")

            c_lob3, c_lob4 = st.columns(2)
            lob_width = c_lob3.number_input("Thickness", 0.5, 5.0, 1.5, step=0.25, key=f"lob_w_{i}")
            lob_color = c_lob4.color_picker("Line Color", "#000000" if i == 0 else "#FF0000", key=f"lob_c_{i}")

            curr_x, curr_y = [], []
            if x_str.strip() and y_str.strip():
                try:
                    curr_x = [float(x.strip()) for x in x_str.split(',') if x.strip()]
                    curr_y = [float(x.strip()) for x in y_str.split(',') if x.strip()]
                except:
                    pass

            if curr_x and curr_y:
                has_data = True

                # For standard plot, we track min/max here.
                # For residual, we calculate min/max after transformation.
                if not is_residual:
                    global_y_min = min(global_y_min, min(curr_y))
                    global_y_max = max(global_y_max, max(curr_y))

                global_x_min = min(global_x_min, min(curr_x))
                global_x_max = max(global_x_max, max(curr_x))

                datasets_to_plot.append({
                    'x': curr_x, 'y': curr_y,
                    'marker': marker_type, 'size': marker_size, 'color': marker_color,
                    'connect': connect_pts,
                    'show_reg': show_reg,
                    'lob_style': lob_style, 'lob_width': lob_width, 'lob_color': lob_color
                })

    # 2. Residual Transformation (If Enabled)
    if is_residual and has_data:
        # Reset Y globals for residual scale
        global_y_min = float('inf')
        global_y_max = float('-inf')

        for ds in datasets_to_plot:
            x_arr = np.array(ds['x'])
            y_arr = np.array(ds['y'])

            # Need at least 2 points for a line
            if len(x_arr) > 1:
                # 1. Calculate Line of Best Fit
                m, c = np.polyfit(x_arr, y_arr, 1)

                # 2. Compute Predicted Y
                y_pred = m * x_arr + c

                # 3. Compute Residuals
                residuals = y_arr - y_pred

                # 4. Update Dataset for Plotting
                ds['y'] = residuals.tolist()

                # Disable regression line for residual plot (it should be flat 0)
                ds['show_reg'] = False

                # Update globals based on residuals
                global_y_min = min(global_y_min, residuals.min())
                global_y_max = max(global_y_max, residuals.max())
            else:
                # Not enough points for regression, can't show residuals
                ds['y'] = []

                # 5. Center Y-Axis around 0
        if global_y_min == float('inf'):
            # Fallback if calculation failed
            global_y_min, global_y_max = -1.0, 1.0
        else:
            # Take the max absolute residual
            max_resid = max(abs(global_y_min), abs(global_y_max))

            if max_resid == 0:
                limit = 1.0
            else:
                # Round up to the nearest integer
                limit = math.ceil(max_resid)

                # Safety check (if ceiling is 0 for some reason)
                if limit == 0:
                    limit = 1.0

            global_y_min = -float(limit)
            global_y_max = float(limit)

    st.markdown("---")
    st.subheader("Domain & Range")

    # Safe defaults if no data
    if not has_data:
        global_x_min, global_x_max = 0.0, 10.0
        global_y_min, global_y_max = 0.0, 20.0
        if is_residual:
            global_y_min, global_y_max = -5.0, 5.0
    else:
        # Standard padding for Scatter (Residuals already padded above)
        if not is_residual:
            global_x_max = math.ceil(global_x_max * 1.1)
            global_y_max = math.ceil(global_y_max * 1.1)
            if global_x_min > 0: global_x_min = 0
            if global_y_min > 0: global_y_min = 0
        else:
            # For residuals, just ensure X is padded similarly to standard
            global_x_max = math.ceil(global_x_max * 1.1)
            if global_x_min > 0: global_x_min = 0

    span_x = (global_x_max - global_x_min) if (global_x_max - global_x_min) > 0 else 10
    span_y = (global_y_max - global_y_min) if (global_y_max - global_y_min) > 0 else 10

    ideal_step_x = 56.7 * span_x / target_width_pts
    ideal_step_y = 56.7 * span_y / target_height_pts


    def get_nice_step(val):
        if val <= 0: return 1.0
        magnitude = 10 ** math.floor(math.log10(val))
        residual = val / magnitude
        if residual < 1.5:
            nice = 1
        elif residual < 3.5:
            nice = 2
        elif residual < 7.5:
            nice = 5
        else:
            nice = 10
        return nice * magnitude


    default_step_x = get_nice_step(ideal_step_x)
    default_step_y = get_nice_step(ideal_step_y)

    c_x1, c_x2, c_x3 = st.columns(3)
    # X Axis keys are static so they don't reset when toggling residual view
    x_min = c_x1.number_input("X Min", -1000.0, 1000.0, float(global_x_min), key="xmin_global")
    x_max = c_x2.number_input("X Max", -1000.0, 1000.0, float(global_x_max), key="xmax_global")
    scale_x = c_x3.number_input("X Step", 0.1, 1000.0, float(default_step_x), key="xstep_global")

    c_y1, c_y2, c_y3 = st.columns(3)
    # Y Axis keys are dynamic (suffix) so they RESET/UPDATE when switching plot modes
    y_key_suffix = "_res" if is_residual else "_std"
    y_min = c_y1.number_input("Y Min", -1000.0, 1000.0, float(global_y_min), key=f"ymin{y_key_suffix}")
    y_max = c_y2.number_input("Y Max", -1000.0, 1000.0, float(global_y_max), key=f"ymax{y_key_suffix}")
    scale_y = c_y3.number_input("Y Step", 0.1, 1000.0, float(default_step_y), key=f"ystep{y_key_suffix}")

    st.markdown("---")
    st.subheader("Appearance")

    # X Axis Row
    c_lbl_x1, c_lbl_x2 = st.columns([3, 1])
    with c_lbl_x1:
        label_x = st.text_input("X Axis Label", "x")
    with c_lbl_x2:
        st.write("")
        st.write("")
        x_label_pos_str = st.selectbox("X Pos", ["Right", "Bottom"], label_visibility="collapsed")

    # Y Axis Row
    c_lbl_y1, c_lbl_y2 = st.columns([3, 1])
    with c_lbl_y1:
        default_y_label = "Residuals" if is_residual else "y"
        label_y = st.text_input("Y Axis Label", default_y_label)
    with c_lbl_y2:
        st.write("")
        st.write("")
        y_label_pos_str = st.selectbox("Y Pos", ["Top (Horizontal)", "Side (Horizontal)", "Side (Vertical)"],
                                       label_visibility="collapsed")

    y_pos_map = {
        "Top (Horizontal)": "top",
        "Side (Horizontal)": "side_horizontal",
        "Side (Vertical)": "side_vertical"
    }
    x_pos_map = {
        "Right": "right",
        "Bottom": "bottom"
    }

# ==========================================
# SIDEBAR: CALIBRATION
# ==========================================
st.sidebar.markdown("---")
with st.sidebar.expander("🔧 Calibration & Diagnostics", expanded=False):
    span_x = x_max - x_min
    span_y = y_max - y_min

    num_major_x = math.ceil(span_x / scale_x)
    num_major_y = math.ceil(span_y / scale_y)

    # Prevent div/0
    if scale_y == 0: scale_y = 1.0
    if scale_x == 0: scale_x = 1.0

    idx_xaxis_row = int((y_max - 0) / scale_y)
    idx_yaxis_col = int((0 - x_min) / scale_x)

    st.markdown("#### Diagnostic Info")

    # Internal Axis Detection
    is_y_internal = (0 < idx_yaxis_col < num_major_x)
    is_x_internal = (0 < idx_xaxis_row < num_major_y)

    col_d1, col_d2 = st.columns(2)
    col_d1.metric("X-Axis Position", f"Row {idx_xaxis_row}" if is_x_internal else (
        "Bottom" if idx_xaxis_row >= num_major_y else "Top/Off"))
    col_d2.metric("Y-Axis Position",
                  f"Col {idx_yaxis_col}" if is_y_internal else ("Left" if idx_yaxis_col <= 0 else "Right/Off"))

    if is_y_internal or is_x_internal:
        st.info("💡 Axes are inside the plot region. Margins will auto-collapse.")

    force_margins = st.checkbox("Force External Margins", value=False,
                                help="Keep wide margins even if axes are internal")

    st.markdown("#### Subdivisions")
    c_sub1, c_sub2 = st.columns(2)
    minor_subs_x = c_sub1.slider("Minor Subs X", 1, 10, 2)
    minor_subs_y = c_sub2.slider("Minor Subs Y", 1, 10, 2)

    st.markdown("#### Axis Label Tuning")

    base_off_x_num = -5.0
    # UPDATED: X Label default -15.0 to lift it up (user requested)
    base_off_x_lbl = -15.0
    base_off_y_lbl_y = 2.0

    if y_label_pos_str == "Top (Horizontal)":
        base_off_y_lbl_x = -2.0
    elif y_label_pos_str == "Side (Vertical)":
        base_off_y_lbl_x = 10.0
    else:
        # UPDATED: Y Label (Side Horiz) default 0.0 (neutral) because backend now anchors to margin
        base_off_y_lbl_x = 0.0

    off_x_num = st.slider("X Numbers Offset Y", -20.0, 20.0, 0.0) + base_off_x_num
    off_x_lbl = st.slider("X Label Offset Y", -50.0, 50.0, 0.0) + base_off_x_lbl

    off_y_lbl_x = st.slider("Y Label Offset X", -50.0, 50.0, 0.0) + base_off_y_lbl_x
    off_y_lbl_y = st.slider("Y Label Offset Y", -50.0, 50.0, 0.0) + base_off_y_lbl_y

    st.markdown("#### Thickness")
    lw_axis = st.slider("Axes Thickness", 0.5, 5.0, 1.5, step=0.25)
    lw_grid_maj = st.slider("Major Grid Thickness", 0.25, 3.0, 0.75, step=0.25)
    lw_grid_min = st.slider("Minor Grid Thickness", 0.1, 2.0, 0.25, step=0.05)

    def_round_x = 0 if float(scale_x).is_integer() else 1
    def_round_y = 0 if float(scale_y).is_integer() else 1
    round_x = st.number_input("X Axis Decimals", 0, 5, def_round_x)
    round_y = st.number_input("Y Axis Decimals", 0, 5, def_round_y)

# ==========================================
# MAIN COLUMN 2: PREVIEW
# ==========================================

avail_grid_width = max(100, target_width_pts - 100)
avail_grid_height = max(100, target_height_pts - 100)

if num_major_x == 0: num_major_x = 1
if num_major_y == 0: num_major_y = 1

minor_spacing_x = avail_grid_width / (num_major_x * minor_subs_x)
minor_spacing_y = avail_grid_height / (num_major_y * minor_subs_y)

config = GraphConfig(
    grid_cols=(int(num_major_x), int(num_major_y)),
    grid_scale=(float(scale_x), float(scale_y)),
    axis_pos=(idx_xaxis_row, idx_yaxis_col),
    axis_labels=(label_x, label_y),
    minor_spacing=(minor_spacing_x, minor_spacing_y),
    minor_per_major=(minor_subs_x, minor_subs_y),
    tick_rounding=(round_x, round_y),

    show_vertical_grid=True,
    show_horizontal_grid=True,
    show_minor_grid=True,
    show_x_axis=True,
    show_y_axis=True,
    show_x_arrow=True,
    show_y_arrow=True,
    show_x_numbers=True,
    show_y_numbers=True,
    show_x_ticks=True,
    show_y_ticks=True,

    axis_thickness=lw_axis,
    grid_thickness_major=lw_grid_maj,
    grid_thickness_minor=lw_grid_min,

    # New Config for Margin Logic
    force_external_margins=force_margins,

    offset_xaxis_num_y=off_x_num,
    offset_xaxis_label_y=off_x_lbl,
    offset_yaxis_label_x=off_y_lbl_x,
    offset_yaxis_label_y=off_y_lbl_y,

    y_label_pos=y_pos_map[y_label_pos_str],
    x_label_pos=x_pos_map[x_label_pos_str]
)

engine = StatsGraphEngine(config)
engine.draw_grid_lines()
engine.draw_axis_labels()

for ds in datasets_to_plot:
    line_params = None
    if ds['show_reg'] and len(ds['x']) > 1:
        try:
            m, c = np.polyfit(ds['x'], ds['y'], 1)
            line_params = (m, c)
        except:
            pass

    engine.draw_scatter(
        ds['x'], ds['y'],
        connect=ds['connect'],
        line_of_best_fit=line_params,
        marker_type=ds['marker'],
        marker_size=ds['size'],
        color=ds['color'],
        lob_color=ds['lob_color'],
        lob_width=ds['lob_width'],
        lob_style=ds['lob_style']
    )

svg_string = engine.get_svg_string()

with col_preview:
    st.subheader("Preview")
    render_interactive_graph(svg_string, engine.width_pixels, engine.height_pixels, target_width_cm, target_height_cm,
                             10)