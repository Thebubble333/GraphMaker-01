import streamlit as st
import math
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.graph_maker import GraphEngine, GraphConfig
from utils.math_analyser import MathAnalyser
from utils.interactive_viewer import render_interactive_graph
from utils.nav import render_sidebar

st.set_page_config(layout="wide", page_title="Function Grapher")
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
st.sidebar.title("📈 Settings")
st.sidebar.header("Grid")

mode = st.sidebar.radio("Input Mode", ["Min/Max Window", "Range & Center"], horizontal=True)

# Defaults
scale_x = 1.0
scale_y = 1.0
minor_spacing_x = 10.0
minor_spacing_y = 10.0
target_width_cm = 12.0
target_height_cm = 12.0
global_xmin = -10.0
global_xmax = 10.0

if mode == "Min/Max Window":
    st.sidebar.markdown("### Window Limits")
    link_xy = st.sidebar.checkbox("Link X/Y Scale", value=False)
    auto_scale = st.sidebar.checkbox("Auto-pick Grid Scale", value=True)

    st.sidebar.markdown("### Target Print Size")
    c_dim1, c_dim2 = st.sidebar.columns(2)
    target_width_cm = c_dim1.number_input("Width (cm)", 5.0, 50.0, 12.0, step=0.5)
    target_height_cm = c_dim2.number_input("Height (cm)", 5.0, 50.0, 12.0, step=0.5)
    target_width_pts = target_width_cm * 28.3465
    target_height_pts = target_height_cm * 28.3465

    st.sidebar.markdown("### Axes")
    c_x1, c_x2 = st.sidebar.columns(2)
    global_xmin = c_x1.number_input("X Min", value=-10.0, step=1.0)
    global_xmax = c_x2.number_input("X Max", value=10.0, step=1.0)

    c_y1, c_y2 = st.sidebar.columns(2)
    ymin = c_y1.number_input("Y Min", value=-10.0, step=1.0)
    ymax = c_y2.number_input("Y Max", value=10.0, step=1.0)

    width_units = global_xmax - global_xmin
    height_units = ymax - ymin


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


    if auto_scale:
        scale_x = calculate_auto_scale_physical(global_xmin, global_xmax, target_width_cm)
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
    axis_x_pos_calc = -global_xmin / scale_x
    axis_y_pos_calc = ymax / scale_y
    axis_x_pos = int(round(axis_x_pos_calc))
    axis_y_pos = int(round(axis_y_pos_calc))

    if x_cols > 0: minor_spacing_x = target_width_pts / (x_cols * 5)
    if y_cols > 0: minor_spacing_y = target_height_pts / (y_cols * 5)
    x_range = x_cols
    y_range = y_cols

else:
    # Range & Center Mode (Simplified for brevity, can copy logic if needed, but layout is the focus)
    c1, c2 = st.sidebar.columns(2)
    x_range = c1.slider("X Range", 5, 50, 10)
    y_range = c2.slider("Y Range", 5, 50, 10)
    global_xmin, global_xmax = -x_range / 2, x_range / 2
    scale_x = 1.0
    scale_y = 1.0
    axis_x_pos = x_range / 2
    axis_y_pos = y_range / 2
    minor_spacing_x = minor_spacing_y = 20.0  # Dummy defaults

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
show_x_nums = c_num1.checkbox("X Scale", value=True)
show_y_nums = c_num2.checkbox("Y Scale", value=True)
c5, c6 = st.sidebar.columns(2)
label_x = c5.text_input("X Label", "x")
label_y = c6.text_input("Y Label", "y")

# --- MAIN LAYOUT ---
col_funcs, col_preview = st.columns([2, 3])

if 'funcs_data' not in st.session_state:
    st.session_state.funcs_data = [
        {'expr': "sin(x)", 'color': "#000000", 'thick': 1.5, 'label': False,
         'use_custom_domain': False, 'dom_min': -5.0, 'dom_max': 5.0,
         'dom_start_style': 'None', 'dom_end_style': 'None',
         'show_y_int': False, 'show_x_int': False, 'show_stat': False,
         'show_inflection': False, 'exact_vals': True}
    ]


def add_func():
    st.session_state.funcs_data.append({
        'expr': "", 'color': "#000000", 'thick': 1.5, 'label': False,
        'use_custom_domain': False, 'dom_min': global_xmin, 'dom_max': global_xmax,
        'dom_start_style': 'None', 'dom_end_style': 'None',
        'show_y_int': False, 'show_x_int': False, 'show_stat': False,
        'show_inflection': False, 'exact_vals': True
    })


def remove_func(idx):
    st.session_state.funcs_data.pop(idx)


with col_funcs:
    st.subheader("Functions")
    for i, func_obj in enumerate(st.session_state.funcs_data):
        with st.expander(f"Function {i + 1}", expanded=True):
            c_expr, c_del = st.columns([5, 1])
            func_obj['expr'] = c_expr.text_input("Expr", func_obj['expr'], key=f"expr_{i}",
                                                 label_visibility="collapsed")
            if c_del.button("🗑️", key=f"del_{i}"):
                remove_func(i)
                st.rerun()

            c_col, c_thk, c_lbl = st.columns([1, 2, 2])
            func_obj['color'] = c_col.color_picker("C", func_obj['color'], key=f"col_{i}", label_visibility="collapsed")
            func_obj['thick'] = c_thk.number_input("Thick", 0.5, 10.0, func_obj['thick'], step=0.5, key=f"thk_{i}",
                                                   label_visibility="collapsed")
            func_obj['label'] = c_lbl.checkbox("Label", func_obj['label'], key=f"lbl_{i}")

            func_obj['use_custom_domain'] = st.checkbox("Restrict Domain", func_obj['use_custom_domain'],
                                                        key=f"use_dom_{i}")
            if func_obj['use_custom_domain']:
                c_d1, c_d2, c_d3, c_d4 = st.columns([2, 3, 3, 2])
                style_opts = ["None", "Filled", "Hollow"]
                func_obj['dom_start_style'] = c_d1.selectbox("Start", style_opts, index=style_opts.index(
                    func_obj.get('dom_start_style', 'None')), key=f"dss_{i}", label_visibility="collapsed")
                func_obj['dom_min'] = c_d2.number_input("Min", value=float(func_obj.get('dom_min', -5.0)),
                                                        key=f"dmin_{i}", label_visibility="collapsed")
                func_obj['dom_max'] = c_d3.number_input("Max", value=float(func_obj.get('dom_max', 5.0)),
                                                        key=f"dmax_{i}", label_visibility="collapsed")
                func_obj['dom_end_style'] = c_d4.selectbox("End", style_opts, index=style_opts.index(
                    func_obj.get('dom_end_style', 'None')), key=f"des_{i}", label_visibility="collapsed")

            c_f1, c_f2 = st.columns(2)
            func_obj['show_y_int'] = c_f1.checkbox("Y-Int", func_obj.get('show_y_int', False), key=f"yint_{i}")
            func_obj['show_x_int'] = c_f2.checkbox("X-Ints", func_obj.get('show_x_int', False), key=f"xint_{i}")
            c_f3, c_f4 = st.columns(2)
            func_obj['show_stat'] = c_f3.checkbox("Stationary", func_obj.get('show_stat', False), key=f"stat_{i}")
            func_obj['show_inflection'] = c_f4.checkbox("Inflection", func_obj.get('show_inflection', False),
                                                        key=f"inf_{i}")
            func_obj['exact_vals'] = st.checkbox("Exact Vals", func_obj.get('exact_vals', True), key=f"exact_{i}")

    if st.button("➕ Add Function"):
        add_func()
        st.rerun()

with col_preview:
    st.subheader("Preview")
    config = GraphConfig(
        grid_cols=(x_range, y_range),
        grid_scale=(scale_x, scale_y),
        axis_pos=(axis_y_pos, axis_x_pos),
        axis_labels=(label_x, label_y),
        minor_spacing=(minor_spacing_x, minor_spacing_y),
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
            if func_obj['use_custom_domain']:
                domain = (func_obj['dom_min'], func_obj['dom_max'])
            else:
                x_min_calc = -1 * scale_x * axis_x_pos
                x_max_calc = scale_x * (x_range - axis_x_pos)
                domain = (x_min_calc, x_max_calc)

            lbl = func_obj['expr'] if func_obj['label'] else None
            engine.plot_function(
                func_obj['expr'],
                domain=domain,
                color=func_obj['color'],
                line_thickness=func_obj['thick'],
                label_text=lbl
            )

            analyser = MathAnalyser(func_obj['expr'])
            show_endpoints = func_obj['use_custom_domain'] and (
                        func_obj['dom_start_style'] != "None" or func_obj['dom_end_style'] != "None")
            ep_styles = (func_obj.get('dom_start_style', 'None').lower(), func_obj.get('dom_end_style', 'None').lower())

            features = analyser.get_features(
                domain=domain,
                show_y_intercept=func_obj['show_y_int'],
                show_x_intercepts=func_obj['show_x_int'],
                show_stationary=func_obj['show_stat'],
                show_inflection=func_obj['show_inflection'],
                show_endpoints=show_endpoints,
                endpoint_types=ep_styles,
                exact_values=func_obj['exact_vals']
            )
            engine.draw_features(features)

    svg_string = engine.get_svg_string()
    render_interactive_graph(svg_string, engine.width_pixels, engine.height_pixels, target_width_cm, target_height_cm,
                             10)