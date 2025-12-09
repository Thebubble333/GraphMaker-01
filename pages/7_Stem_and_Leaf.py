import streamlit as st
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.graph_maker import GraphConfig
from utils.graph_stats import StatsGraphEngine
from utils.interactive_viewer import render_interactive_graph
from utils.nav import render_sidebar

st.set_page_config(layout="wide", page_title="Stem & Leaf Plots")
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

st.title("Stem & Leaf Plotter")

# --- SIDEBAR ---
st.sidebar.title("⚙️ Settings")
# Reduced defaults
target_width_cm = st.sidebar.number_input("Width (cm)", 5.0, 50.0, 10.0, step=0.5)
target_height_cm = st.sidebar.number_input("Height (cm)", 5.0, 50.0, 8.0, step=0.5)

st.sidebar.markdown("### Styling")
font_size = st.sidebar.slider("Font Size", 8, 24, 14)
row_h = st.sidebar.slider("Row Height", 15, 50, 25)
col_w = st.sidebar.slider("Column Spacing", 10, 40, 20)

st.sidebar.markdown("### Data Logic")
stem_unit = st.sidebar.selectbox("Stem Unit", [1, 10, 100, 1000, 0.1], index=1, 
                               help="The value of the stem place.")
split_stems = st.sidebar.checkbox("Split Stems (Halves)", value=False, 
                                  help="Splits each stem into two rows: 0-4 and 5-9.")
show_quartiles = st.sidebar.checkbox("Highlight Q1/Med/Q3", value=False,
                                     help="Draws red circles (Median) and blue bars (Quartiles).")
debug_mode = st.sidebar.checkbox("Debug Mode", value=False, help="Draws lines connecting data points.")

# --- MAIN ---
col_data, col_preview = st.columns([1, 2])

with col_data:
    st.subheader("Data Input")
    
    plot_type = st.radio("Plot Type", ["Single", "Back-to-Back"])
    
    data_left = []
    data_right = []
    
    if plot_type == "Back-to-Back":
        left_input = st.text_area("Left Side Data (e.g. Group A)", "12, 15, 18, 22, 25, 29, 31, 32", height=100)
        left_label = st.text_input("Left Label", "Group A")
        
        right_input = st.text_area("Right Side Data (e.g. Group B)", "14, 19, 21, 24, 28, 32, 35, 41, 42", height=100)
        right_label = st.text_input("Right Label", "Group B")
        
        try:
            if left_input.strip():
                data_left = [float(x.strip()) for x in left_input.split(',') if x.strip()]
            if right_input.strip():
                data_right = [float(x.strip()) for x in right_input.split(',') if x.strip()]
        except ValueError:
            st.error("Invalid input numbers")
            
    else:
        left_input = st.text_area("Data Values", "41, 42, 45, 50, 52, 58, 60, 61", height=150)
        left_label = st.text_input("Title", "My Data")
        right_label = "" 
        
        try:
            if left_input.strip():
                data_left = [float(x.strip()) for x in left_input.split(',') if x.strip()]
        except ValueError:
            st.error("Invalid input numbers")

    if data_left or data_right:
        sample = data_left[0] if data_left else (data_right[0] if data_right else 42)
        stem = int(sample // stem_unit)
        leaf = int((sample % stem_unit) // (stem_unit/10))
        val_str = f"{int(sample)}" if sample.is_integer() else f"{sample}"
        default_key = f"Key: {stem} | {leaf} = {val_str}"
    else:
        default_key = "Key: 4 | 2 = 42"
        
    key_text = st.text_input("Key Description", default_key)

with col_preview:
    if data_left or data_right:
        w_px = target_width_cm * 28.3465
        h_px = target_height_cm * 28.3465
        
        config = GraphConfig(
            grid_cols=(1, 1),
            show_border=False,
            show_x_axis=False,
            show_y_axis=False,
            show_vertical_grid=False,
            show_horizontal_grid=False,
            force_external_margins=True
        )
        
        engine = StatsGraphEngine(config)
        engine.width_pixels = w_px
        engine.height_pixels = h_px
        engine.dwg['viewBox'] = f"0 0 {w_px} {h_px}"
        
        engine.draw_stem_and_leaf(
            left_data=data_left,
            right_data=data_right if plot_type == "Back-to-Back" else [],
            title_left=left_label,
            title_right=right_label,
            stem_value=stem_unit,
            key_label=key_text,
            font_size=font_size,
            row_height=row_h,
            col_width=col_w,
            split_stems=split_stems,
            show_quartiles=show_quartiles,
            debug_mode=debug_mode 
        )
        
        svg = engine.get_svg_string()
        render_interactive_graph(svg, w_px, h_px, target_width_cm, target_height_cm, 10)
        
    else:
        st.info("Enter data to visualize.")