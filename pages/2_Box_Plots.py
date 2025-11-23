import streamlit as st
import math
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.graph_maker import GraphEngine, GraphConfig
from utils.stats_analyser import StatsAnalyser
from utils.interactive_viewer import render_interactive_graph
from utils.nav import render_sidebar

st.set_page_config(layout="wide", page_title="Box Plots")
render_sidebar()

# --- CSS Tweaks ---
st.markdown("""
    <style>
        /* Hide the Streamlit Top Bar (Deploy button, etc) */
        header {visibility: hidden;}

        /* Add padding to top of main container so it doesn't clip */
        .block-container { 
            padding-top: 3rem !important; 
            padding-bottom: 1rem; 
        } 

        /* --- SIDEBAR COMPACTING --- */
        /* Reduce the massive default padding at the top of the sidebar */
        [data-testid="stSidebarUserContent"] {
            padding-top: 1.5rem;
        }

        /* Reduce margins around the divider (hr) in the sidebar */
        [data-testid="stSidebar"] hr {
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }

        /* Tighten the title "Settings" */
        [data-testid="stSidebar"] h1 {
            padding-top: 0rem !important;
            margin-top: 0rem !important;
            font-size: 1.8rem;
        }

        /* Reduce gap between elements */
        [data-testid="stSidebar"] .stElementContainer {
            margin-bottom: 0.5rem;
        }

        div[data-testid="column"] { padding: 0px; }
        .stTextArea textarea { font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: Global Settings ---
st.sidebar.title("📦 Settings")

st.sidebar.markdown("### Target Print Size")
target_width_cm = st.sidebar.number_input("Width (cm)", 5.0, 50.0, 12.0, step=0.5)
target_height_cm = st.sidebar.number_input("Height (cm)", 5.0, 50.0, 6.0, step=0.5)
target_width_pts = target_width_cm * 28.3465
target_height_pts = target_height_cm * 28.3465

st.sidebar.markdown("### Axis Range")
# Initialize session state for auto-scaling if not present
if 'bp_xmin' not in st.session_state:
    st.session_state.bp_xmin = 0.0
    st.session_state.bp_xmax = 40.0
    st.session_state.bp_scale = 2.0
    st.session_state.bp_last_data = ""

c1, c2 = st.sidebar.columns(2)
x_min = c1.number_input("Min", -1000.0, 1000.0, st.session_state.bp_xmin, step=1.0)
x_max = c2.number_input("Max", -1000.0, 1000.0, st.session_state.bp_xmax, step=1.0)
scale_x = st.sidebar.number_input("Grid Scale", 0.1, 5000.0, st.session_state.bp_scale)
label_x = st.sidebar.text_input("Axis Label", r"axis label (\units)")

show_label_bg = st.sidebar.checkbox("Label Backgrounds", value=True)
# CHANGED: Default opacity set to 1.0
bg_opacity = 1.0
if show_label_bg:
    bg_opacity = st.sidebar.slider("Opacity", 0.0, 1.0, 1.0, step=0.05)

with st.sidebar.expander("Advanced Calibration"):
    minor_subs = st.slider("Minor Subdivisions", 1, 10, 5)
    off_box_lbl = st.slider("Box Label Y", -50.0, 50.0, -8.0, step=1.0)
    off_x_num = st.slider("Axis Numbers Y", -50.0, 50.0, 10.0, step=1.0)
    off_x_lbl = st.slider("Axis Label Y", -50.0, 50.0, 6.0, step=1.0)

# --- MAIN LAYOUT ---
col_data, col_preview = st.columns([2, 3])

# --- LEFT COLUMN: Data Entry ---
with col_data:
    st.subheader("Data Samples")

    # Session state for dynamic number of samples
    if 'num_box_samples' not in st.session_state:
        st.session_state.num_box_samples = 2


    def add_sample():
        st.session_state.num_box_samples += 1


    def remove_sample():
        if st.session_state.num_box_samples > 1:
            st.session_state.num_box_samples -= 1


    # Render Sample Inputs
    box_data = []
    all_values_for_scaling = []

    for i in range(st.session_state.num_box_samples):
        with st.expander(f"Sample {i + 1}", expanded=True):
            # Default data examples
            def_val = "12, 15, 18, 22, 22, 25, 30" if i == 0 else "10, 14, 19, 21, 24, 28, 32"
            if i > 1: def_val = ""

            c_lbl, c_vals = st.columns([1, 3])
            lbl = c_lbl.text_input("Label", f"Sample {i + 1}", key=f"lbl_{i}")
            val_str = c_vals.text_area("Values (comma separated)", def_val, height=70, key=f"vals_{i}",
                                       label_visibility="collapsed")

            try:
                vals = [float(x.strip()) for x in val_str.split(',') if x.strip()]
                if vals:
                    box_data.append({"label": lbl, "values": vals})
                    all_values_for_scaling.extend(vals)
            except:
                pass

    # Add/Remove Buttons
    c_add, c_rem, _ = st.columns([1, 1, 2])
    c_add.button("➕ Add Sample", on_click=add_sample)
    c_rem.button("➖ Remove", on_click=remove_sample)

    # --- AUTO SCALE LOGIC (Hidden but active) ---
    current_sig = str(all_values_for_scaling)
    if current_sig != st.session_state.bp_last_data and all_values_for_scaling:
        st.session_state.bp_last_data = current_sig
        d_min, d_max = min(all_values_for_scaling), max(all_values_for_scaling)
        span = d_max - d_min if d_max != d_min else 10

        # Heuristic: Pad by 10% and snap to nearest 2
        new_min = math.floor((d_min - span * 0.1) / 2.0) * 2.0
        new_max = math.ceil((d_max + span * 0.1) / 2.0) * 2.0

        raw_span = (new_max - new_min) / 8
        if raw_span < 0.75:
            sc = 0.5
        elif raw_span < 1.5:
            sc = 1.0
        elif raw_span < 3.5:
            sc = 2.0
        elif raw_span < 7.5:
            sc = 5.0
        else:
            sc = 10.0

        st.session_state.bp_xmin = float(new_min)
        st.session_state.bp_xmax = float(new_max)
        st.session_state.bp_scale = float(sc)
        st.rerun()

# --- RIGHT COLUMN: Preview ---
with col_preview:
    # Calculation
    width_units = x_max - x_min
    if width_units <= 0: width_units = 1.0

    num_major_x = math.ceil(width_units / scale_x)
    if num_major_x < 1: num_major_x = 1

    pixels_per_unit_x = target_width_pts / width_units
    minor_spacing_x = (pixels_per_unit_x * scale_x) / minor_subs
    minor_spacing_y = minor_spacing_x

    # Calculate needed height based on pixel density
    # We want the box plot to fit in the target height
    num_major_y = int(target_height_pts / (minor_spacing_y * minor_subs)) + 1

    axis_pos_x = -x_min / scale_x
    axis_pos_y = num_major_y

    config = GraphConfig(
        grid_cols=(int(num_major_x), int(num_major_y)),
        grid_scale=(scale_x, 1.0),
        axis_pos=(int(axis_pos_y), int(axis_pos_x)),
        axis_labels=(label_x, ""),
        minor_spacing=(minor_spacing_x, minor_spacing_y),
        minor_per_major=(minor_subs, minor_subs),
        show_vertical_grid=True,
        show_horizontal_grid=False,
        show_minor_grid=False,
        show_y_axis=False,
        show_border=True,
        show_x_axis=False,
        show_whisker_caps=False,
        show_x_ticks=False,
        show_label_background=show_label_bg,
        label_background_opacity=bg_opacity,
        offset_box_label_y=off_box_lbl,
        offset_xaxis_num_y=off_x_num,
        offset_xaxis_label_y=off_x_lbl
    )

    engine = GraphEngine(config)
    engine.draw_grid_lines()
    engine.draw_axis_labels()

    analyser = StatsAnalyser()
    if box_data:
        stats_list = [analyser.get_boxplot_stats(item['values'], item['label']) for item in box_data]
        available_h = engine.height_pixels - engine.margin_top - engine.margin_bottom
        step = available_h / (len(stats_list) + 1)
        offsets = [step * (i + 1) for i in range(len(stats_list))]
        engine.draw_box_plots(stats_list, offsets=offsets)

    st.subheader("Preview")
    svg_string = engine.get_svg_string()
    render_interactive_graph(svg_string, engine.width_pixels, engine.height_pixels, target_width_cm, target_height_cm,
                             10)