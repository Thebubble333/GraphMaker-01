import streamlit as st
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.graph_maker import GraphConfig
from utils.graph_stats import StatsGraphEngine
from utils.stats_analyser import StatsAnalyser
from utils.interactive_viewer import render_interactive_graph
from utils.nav import render_sidebar

st.set_page_config(layout="wide", page_title="Visual Quartiles")
render_sidebar()

# --- CSS ---
st.markdown("""
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 2rem !important; }
        div[data-testid="column"] { padding: 0px; }
        .stTextArea textarea { font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# --- MAIN PAGE LAYOUT ---
st.title("Visual Quartile Finder")
col_input, col_preview = st.columns([1, 2])

# ==========================================
# 1. PROCESS DATA FIRST (To Determine Defaults)
# ==========================================
with col_input:
    st.subheader("Data Input")
    default_data = "3, 4, 6, 8, 10, 12, 15"
    raw_input = st.text_area("Enter numbers (comma separated)", default_data, height=150)
    
    vals = []
    error_msg = ""
    try:
        if raw_input.strip():
            vals = sorted([float(x.strip()) for x in raw_input.split(',') if x.strip()])
    except ValueError:
        error_msg = "Invalid input: Please enter numbers only."

    if vals:
        st.info(f"**Sorted Data (n={len(vals)}):**\n\n {vals}")
    
    if error_msg:
        st.error(error_msg)

# Calculate Stats immediately if data exists
analyser = StatsAnalyser()
vq_data = None
if vals:
    vq_data = analyser.get_visual_quartiles(vals)

# ==========================================
# 2. DETERMINE SMART DEFAULTS
# ==========================================
# Default: Red (#FF0000) for Exact/Circle, Blue (#0000FF) for Split/Bar
def_q1 = "#0000FF"
def_med = "#FF0000"
def_q3 = "#0000FF"

if vq_data:
    def_q1 = "#FF0000" if vq_data.q1.type == "exact" else "#0000FF"
    def_med = "#FF0000" if vq_data.median.type == "exact" else "#0000FF"
    def_q3 = "#FF0000" if vq_data.q3.type == "exact" else "#0000FF"

# ==========================================
# 3. SIDEBAR SETTINGS
# ==========================================
st.sidebar.title("⚙️ Display Settings")

target_width_cm = st.sidebar.number_input("Width (cm)", 10.0, 50.0, 18.0, step=0.5)
target_height_cm = st.sidebar.number_input("Height (cm)", 5.0, 30.0, 8.0, step=0.5)

target_width_pts = target_width_cm * 28.3465
target_height_pts = target_height_cm * 28.3465

# --- STYLING ---
st.sidebar.markdown("### Styling")
circle_radius = st.sidebar.slider("Circle Radius", 10, 40, 20)
spacing_factor = st.sidebar.slider("Spacing Spread", 0.5, 2.0, 1.0)
font_size_nums = st.sidebar.slider("Number Font Size", 8, 24, 14)

hl_radius_offset = st.sidebar.slider("Highlight Ring Offset", 0, 15, 4)
hl_thickness = st.sidebar.slider("Highlight Thickness", 1, 10, 3)

# --- COLORS (With Smart Defaults) ---
st.sidebar.markdown("### Colors")
c1, c2, c3 = st.sidebar.columns(3)

# We use the calculated defaults here. 
# Note: Changing data updates the default, but if user manually picked a color, 
# Streamlit might persist that manual choice depending on session state behavior.
col_q1 = c1.color_picker("Q1", def_q1) 
col_med = c2.color_picker("Median", def_med)
col_q3 = c3.color_picker("Q3", def_q3)

# --- POSITIONING ---
st.sidebar.markdown("### Positioning")
arrow_len = st.sidebar.slider("Base Arrow Length", 20, 100, 30)
q_arrow_drop = st.sidebar.slider("Q1/Q3 Extra Drop", 0, 100, 0)
legend_y_pos = st.sidebar.slider("Legend Y Offset", -50, 50, 10)
show_legend = st.sidebar.checkbox("Show Legend", value=True)

# ==========================================
# 4. RENDER GRAPH
# ==========================================
with col_preview:
    if vq_data:
        # Configure Graph Engine
        config = GraphConfig(
            grid_cols=(1, 1),
            font_size=12,
            show_border=False,
            show_x_axis=False,
            show_y_axis=False,
            show_vertical_grid=False,
            show_horizontal_grid=False,
            force_external_margins=True
        )
        
        engine = StatsGraphEngine(config)
        
        engine.width_pixels = target_width_pts
        engine.height_pixels = target_height_pts
        engine.dwg['viewBox'] = f"0 0 {target_width_pts} {target_height_pts}"

        # Draw with the selected colors
        engine.draw_visual_quartiles(
            vq_data, 
            radius=circle_radius, 
            spread=spacing_factor, 
            font_size=font_size_nums,
            show_legend=show_legend,
            arrow_len=arrow_len,
            q_arrow_offset=q_arrow_drop,
            legend_y_offset=legend_y_pos,
            highlight_offset=hl_radius_offset,
            highlight_width=hl_thickness,
            color_q1=col_q1,
            color_med=col_med,
            color_q3=col_q3
        )

        svg_string = engine.get_svg_string()
        render_interactive_graph(svg_string, engine.width_pixels, engine.height_pixels, target_width_cm, target_height_cm, 10)
    else:
        st.warning("Please enter data to generate visualization.")