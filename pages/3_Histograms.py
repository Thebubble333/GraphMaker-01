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

st.set_page_config(layout="wide", page_title="Histograms")
render_sidebar()

# --- CSS Tweaks ---
st.markdown("""
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 2rem !important; padding-bottom: 1rem; } 
        div[data-testid="column"] { padding: 0px; }
        .stTextArea textarea { font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# LAYOUT SETUP
# ==========================================
col_data, col_preview = st.columns([1, 2])

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
# MAIN COLUMN 1: DATA & LABELS
# ==========================================
with col_data:
    st.subheader("Data Input")
    input_mode = st.radio("Input Mode", ["Raw Data (List of Numbers)", "Frequency Data (Counts)"], index=0)

    raw_input = ""
    freq_input = ""
    start_val = 0.0
    bin_width = 5.0

    if input_mode == "Raw Data (List of Numbers)":
        raw_input = st.text_area("Raw Values", "12, 15, 18, 22, 22, 25, 29, 31, 35, 42", height=100)
        c1, c2 = st.columns(2)
        start_val = c1.number_input("Start Value (Bin Min)", 0.0, 1000.0, 10.0)
        bin_width = c2.number_input("Bin Width", 0.1, 500.0, 5.0)
    else:
        freq_input = st.text_area("Frequencies", "2, 5, 8, 3, 1", height=100)
        c1, c2 = st.columns(2)
        start_val = c1.number_input("Start Value (Left Edge)", 0.0, 1000.0, 10.0)
        bin_width = c2.number_input("Bin Width (Scale)", 0.1, 500.0, 5.0)

    st.markdown("---")
    st.subheader("Labels & Style")
    lbl_mode = st.selectbox("Label Style", ["Intervals (Continuous)", "Centered (Discrete Categories)"])

    l1, l2 = st.columns(2)
    label_x = l1.text_input("X Axis Label", "Score")
    label_y = l2.text_input("Y Axis Label", "Frequency")

    # --- Position Selectors (Updated to match Scatter Plots) ---
    c_pos1, c_pos2 = st.columns(2)
    # Defaulting to Bottom and Side (Horizontal) as requested
    x_label_pos_str = c_pos1.selectbox("X Label Pos", ["Bottom", "Right"], index=0)
    y_label_pos_str = c_pos2.selectbox("Y Label Pos", ["Side (Horizontal)", "Top (Horizontal)", "Side (Vertical)"],
                                       index=0)

    y_pos_map = {
        "Top (Horizontal)": "top",
        "Side (Horizontal)": "side_horizontal",
        "Side (Vertical)": "side_vertical"
    }
    x_pos_map = {
        "Right": "right",
        "Bottom": "bottom"
    }

    c_tick1, c_tick2 = st.columns(2)
    show_major_ticks_x = c_tick1.checkbox("Show X Major Ticks", value=False)
    show_major_ticks_y = c_tick2.checkbox("Show Y Major Ticks", value=False)

    st.subheader("Appearance")
    c_col1, c_col2 = st.columns(2)
    hist_color = c_col1.color_picker("Histogram Color", "#e0e0e0")

    # Line Weights
    with st.expander("Line Weights", expanded=False):
        lw_axis = st.slider("Axes Thickness", 0.5, 5.0, 1.5, step=0.25)
        lw_grid_maj = st.slider("Major Grid Thickness", 0.25, 3.0, 0.75, step=0.25)
        lw_grid_min = st.slider("Minor Grid Thickness", 0.1, 2.0, 0.25, step=0.05)
        lw_hist_box = st.slider("Histogram Box Thickness", 0.5, 5.0, 1.2, step=0.1)

# ==========================================
# DATA PROCESSING
# ==========================================

final_freqs = []
final_start = start_val
final_width = bin_width
data_error = None

try:
    if input_mode == "Raw Data (List of Numbers)":
        if raw_input.strip():
            vals = [float(x.strip()) for x in raw_input.split(',') if x.strip()]
            if vals:
                max_val = max(vals)
                if max_val < start_val:
                    data_error = "Max value is lower than Start Value."
                else:
                    num_bins_needed = math.ceil((max_val - start_val) / bin_width)
                    if num_bins_needed == 0: num_bins_needed = 1
                    edges = [start_val + i * bin_width for i in range(num_bins_needed + 1)]
                    hist, _ = np.histogram(vals, bins=edges)
                    final_freqs = hist.tolist()
    else:
        if freq_input.strip():
            final_freqs = [float(x.strip()) for x in freq_input.split(',') if x.strip()]

except Exception as e:
    data_error = f"Error parsing data: {e}"

# ==========================================
# SIDEBAR: ADVANCED CALIBRATION
# ==========================================
st.sidebar.markdown("---")
with st.sidebar.expander("🔧 Manual Calibration", expanded=False):
    # --- AUTO CALCULATION ---
    auto_y_max = max(final_freqs) if final_freqs else 10
    if auto_y_max <= 5:
        auto_y_max = 5
    elif auto_y_max <= 10:
        auto_y_max = 10
    else:
        auto_y_max = math.ceil(auto_y_max * 1.1)

    auto_num_bins = len(final_freqs) if final_freqs else 5
    abs_max_x = final_start + (auto_num_bins * final_width)

    default_scale_x = final_width
    default_scale_y = 1.0
    if auto_y_max > 20: default_scale_y = 5.0
    if auto_y_max > 50: default_scale_y = 10.0

    override_scales = st.checkbox("Override Auto-Scale", value=False)

    if override_scales:
        grid_scale_x = st.number_input("Grid Scale X", 0.1, 1000.0, default_scale_x)
        grid_scale_y = st.number_input("Grid Scale Y", 0.1, 1000.0, default_scale_y)

        needed_cols = math.ceil(abs_max_x / grid_scale_x)
        needed_rows = math.ceil(auto_y_max / grid_scale_y)

        num_major_x = st.number_input("Grid Columns", 1, 200, needed_cols)
        num_major_y = st.number_input("Grid Rows", 1, 200, needed_rows)
    else:
        grid_scale_x = default_scale_x
        grid_scale_y = default_scale_y
        num_major_x = math.ceil(abs_max_x / grid_scale_x)
        num_major_y = math.ceil(auto_y_max / grid_scale_y)

    st.markdown("#### Subdivisions & Offsets")
    c_sub1, c_sub2 = st.columns(2)
    minor_subs_x = c_sub1.slider("Minor Subs X", 1, 10, 1)
    minor_subs_y = c_sub2.slider("Minor Subs Y", 1, 10, 2)

    # --- OFFSETS (Updated to match Scatter Plots logic) ---

    # Defaults from Scatter Plots
    base_off_x_num = -5.0
    base_off_x_lbl = 0.0  # Reset to 0.0 (was -15.0) to push down 15px

    if y_label_pos_str == "Top (Horizontal)":
        base_off_y_lbl_x = -2.0
    elif y_label_pos_str == "Side (Vertical)":
        base_off_y_lbl_x = 10.0
    else:
        # Side Horizontal
        base_off_y_lbl_x = 0.0

    off_x_num = st.slider("X Numbers Offset Y", -20.0, 20.0, 0.0)
    off_x_lbl = st.slider("X Label Offset Y", -50.0, 50.0, 0.0)
    off_y_lbl_x = st.slider("Y Label Offset X", -50.0, 50.0, 0.0)

    final_off_x_num = off_x_num + base_off_x_num
    final_off_x_lbl = off_x_lbl + base_off_x_lbl
    final_off_y_lbl_x = off_y_lbl_x + base_off_y_lbl_x

    def_round_x = 0 if float(grid_scale_x).is_integer() else 1
    def_round_y = 0 if float(grid_scale_y).is_integer() else 1
    round_x = st.number_input("X Axis Decimals", 0, 5, def_round_x)
    round_y = st.number_input("Y Axis Decimals", 0, 5, def_round_y)

# ==========================================
# MAIN COLUMN 2: PREVIEW
# ==========================================

if data_error:
    st.error(data_error)
else:
    avail_grid_width = max(100, target_width_pts - 100)
    avail_grid_height = max(100, target_height_pts - 100)

    minor_spacing_x = avail_grid_width / (num_major_x * minor_subs_x)
    minor_spacing_y = avail_grid_height / (num_major_y * minor_subs_y)

    if lbl_mode.startswith("Centered"):
        hist_label_mode = "center"
        show_grid_numbers_x = False
    else:
        hist_label_mode = None
        show_grid_numbers_x = True

    config = GraphConfig(
        grid_cols=(int(num_major_x), int(num_major_y)),
        grid_scale=(float(grid_scale_x), float(grid_scale_y)),
        axis_pos=(int(num_major_y), 0),
        axis_labels=(label_x, label_y),
        minor_spacing=(minor_spacing_x, minor_spacing_y),
        minor_per_major=(minor_subs_x, minor_subs_y),
        tick_rounding=(round_x, round_y),

        # Aesthetic Toggles
        show_vertical_grid=True,
        show_horizontal_grid=True,
        show_minor_grid=True,
        show_x_axis=True,
        show_y_axis=True,
        show_x_arrow=False,
        show_y_arrow=False,
        show_border=False,

        # --- THICKNESS SETTINGS ---
        axis_thickness=lw_axis,
        grid_thickness_major=lw_grid_maj,
        grid_thickness_minor=lw_grid_min,

        # --- TICK VISIBILITY ---
        show_x_ticks=show_major_ticks_x,
        show_y_ticks=show_major_ticks_y,
        show_x_numbers=show_grid_numbers_x,

        # --- OFFSETS ---
        offset_xaxis_num_y=final_off_x_num,
        offset_xaxis_label_y=final_off_x_lbl,
        offset_yaxis_label_x=final_off_y_lbl_x,

        # --- POSITIONS (New) ---
        y_label_pos=y_pos_map[y_label_pos_str],
        x_label_pos=x_pos_map[x_label_pos_str]
    )

    engine = StatsGraphEngine(config)
    engine.draw_grid_lines()
    engine.draw_axis_labels()

    if final_freqs:
        engine.draw_histogram(
            final_freqs,
            start_val=final_start,
            bin_width=final_width,
            label_mode=hist_label_mode,
            fill_color=hist_color,
            stroke_width=lw_hist_box
        )

    svg_string = engine.get_svg_string()

    with col_preview:
        st.subheader("Graph Preview")
        render_interactive_graph(svg_string, engine.width_pixels, engine.height_pixels, target_width_cm,
                                 target_height_cm, 10)