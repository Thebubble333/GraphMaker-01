import streamlit as st
import math
from graph_maker import GraphEngine, GraphConfig
from math_analyser import MathAnalyser
from interactive_viewer import render_interactive_graph

# 1. Layout "wide" allows us to use columns effectively
st.set_page_config(layout="wide", page_title="GraphMaker")

# --- CSS HACKS FOR COMPACT UI ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem; 
            padding-bottom: 1rem;
        }
        div[data-testid="column"] {
            padding: 0px;
        }
        iframe {
            width: 100%;
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

# Store grid bounds globally so we can default functions to this domain
global_xmin = -10.0
global_xmax = 10.0

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
    global_xmin = c_x1.number_input("X Min", value=-10.0, step=1.0)
    global_xmax = c_x2.number_input("X Max", value=10.0, step=1.0)

    c_y1, c_y2 = st.sidebar.columns(2)
    ymin = c_y1.number_input("Y Min", value=-10.0, step=1.0)
    ymax = c_y2.number_input("Y Max", value=10.0, step=1.0)

    width_units = global_xmax - global_xmin
    height_units = ymax - ymin

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
            scale_y = c_s2.number_input("Y Scale", 0.1, 10.0, 1.0)

    x_cols = max(1, math.ceil(width_units / scale_x))
    y_cols = max(1, math.ceil(height_units / scale_y))

    # CORRECTED LOGIC: Calculate axis offset from Top-Left corner
    axis_x_pos_calc = -global_xmin / scale_x
    axis_y_pos_calc = ymax / scale_y

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

    global_xmin = -x_range / 2
    global_xmax = x_range / 2

    link_xy = st.sidebar.checkbox("Link X/Y Scale", value=True)
    if link_xy:
        scale_x = st.sidebar.number_input("Grid Scale (Units per tick)", 0.1, 10.0, 1.0)
        scale_y = scale_x
    else:
        c_s1, c_s2 = st.sidebar.columns(2)
        scale_x = c_s1.number_input("X Scale", 0.1, 10.0, 1.0)
        scale_y = c_s2.number_input("Y Scale", 0.1, 10.0, 1.0)

    c3, c4 = st.sidebar.columns(2)
    slider_x = c3.slider("Y-Axis Position (from left)", 0, x_range, int(x_range / 2))
    slider_y = c4.slider("X-Axis Position (from bottom)", 0, y_range, int(y_range / 2))

    axis_x_pos = slider_x
    axis_y_pos = y_range - slider_y

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

show_label_bg = st.sidebar.checkbox("Label Backgrounds", value=True)
bg_opacity = 0.85
if show_label_bg:
    bg_opacity = st.sidebar.slider("Opacity", 0.0, 1.0, 0.85, step=0.05)

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
        {
            'expr': "sin(x)",
            'color': "#000000",
            'thick': 1.5,
            'label': False,
            'use_custom_domain': False,
            'dom_min': -5.0,
            'dom_max': 5.0,
            'dom_start_style': 'None',  # None, Filled, Hollow
            'dom_end_style': 'None',
            'show_y_int': False,
            'show_x_int': False,
            'show_stat': False,
            'show_inflection': False,
            'exact_vals': True
        }
    ]


def add_func():
    st.session_state.funcs_data.append({
        'expr': "",
        'color': "#000000",
        'thick': 1.5,
        'label': False,
        'use_custom_domain': False,
        'dom_min': global_xmin,
        'dom_max': global_xmax,
        'dom_start_style': 'None',
        'dom_end_style': 'None',
        'show_y_int': False,
        'show_x_int': False,
        'show_stat': False,
        'show_inflection': False,
        'exact_vals': True
    })


def remove_func(idx):
    st.session_state.funcs_data.pop(idx)


# --- LEFT COLUMN: Functions ---
with col_funcs:
    st.subheader("Functions")

    for i, func_obj in enumerate(st.session_state.funcs_data):
        with st.expander(f"Function {i + 1}", expanded=True):
            # Row 1: Expression and Delete
            c_expr, c_del = st.columns([5, 1])
            func_obj['expr'] = c_expr.text_input("Expression", func_obj['expr'], key=f"expr_{i}",
                                                 label_visibility="collapsed", placeholder="e.g. x^2 - 4")
            if c_del.button("🗑️", key=f"del_{i}"):
                remove_func(i)
                st.rerun()

            # Row 2: Appearance
            c_col, c_thk, c_lbl = st.columns([1, 2, 2])
            current_col = func_obj['color']
            if not current_col.startswith('#'):
                current_col = NAME_TO_HEX.get(current_col, "#000000")
            func_obj['color'] = c_col.color_picker("C", current_col, key=f"col_{i}", label_visibility="collapsed")
            func_obj['thick'] = c_thk.number_input("Thick", 0.5, 10.0, func_obj['thick'], step=0.5, key=f"thk_{i}",
                                                   label_visibility="collapsed")
            func_obj['label'] = c_lbl.checkbox("Show Label", func_obj['label'], key=f"lbl_{i}")

            # Row 3: Domain & Endpoints
            st.markdown("---")
            func_obj['use_custom_domain'] = st.checkbox("Restrict Domain", func_obj['use_custom_domain'],
                                                        key=f"use_dom_{i}")

            if func_obj['use_custom_domain']:
                c_d1, c_d2, c_d3, c_d4 = st.columns([2, 3, 3, 2])

                # Styles
                style_opts = ["None", "Filled", "Hollow"]

                func_obj['dom_start_style'] = c_d1.selectbox("Start", style_opts, index=style_opts.index(
                    func_obj.get('dom_start_style', 'None')), key=f"dss_{i}", label_visibility="collapsed")
                func_obj['dom_min'] = c_d2.number_input("Min", value=float(func_obj.get('dom_min', -5.0)),
                                                        key=f"dmin_{i}", label_visibility="collapsed")
                func_obj['dom_max'] = c_d3.number_input("Max", value=float(func_obj.get('dom_max', 5.0)),
                                                        key=f"dmax_{i}", label_visibility="collapsed")
                func_obj['dom_end_style'] = c_d4.selectbox("End", style_opts, index=style_opts.index(
                    func_obj.get('dom_end_style', 'None')), key=f"des_{i}", label_visibility="collapsed")

            # Row 4: Key Features
            st.markdown("###### Key Features")
            c_f1, c_f2 = st.columns(2)
            func_obj['show_y_int'] = c_f1.checkbox("Y-Intercept", func_obj.get('show_y_int', False), key=f"yint_{i}")
            func_obj['show_x_int'] = c_f2.checkbox("X-Intercepts", func_obj.get('show_x_int', False), key=f"xint_{i}")

            c_f3, c_f4 = st.columns(2)
            func_obj['show_stat'] = c_f3.checkbox("Stationary Pts", func_obj.get('show_stat', False), key=f"stat_{i}")
            func_obj['show_inflection'] = c_f4.checkbox("Inflection Pts", func_obj.get('show_inflection', False),
                                                        key=f"inf_{i}")

            func_obj['exact_vals'] = st.checkbox("Use Exact Values (Surds/Pi)", func_obj.get('exact_vals', True),
                                                 key=f"exact_{i}")

    if st.button("➕ Add Function"):
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
        show_y_ticks=show_y_ticks,
        show_label_background=show_label_bg,  # New config
        label_background_opacity=bg_opacity  # New config
    )

    engine = GraphEngine(config)
    engine.draw_grid_lines()
    engine.draw_axis_labels()

    for func_obj in st.session_state.funcs_data:
        if func_obj['expr'].strip():
            # Determine Domain
            if func_obj['use_custom_domain']:
                domain = (func_obj['dom_min'], func_obj['dom_max'])
            else:
                x_min_calc = -1 * scale_x * axis_x_pos
                x_max_calc = scale_x * (x_range - axis_x_pos)
                domain = (x_min_calc, x_max_calc)

            # 1. Plot the Curve
            lbl = func_obj['expr'] if func_obj['label'] else None
            engine.plot_function(
                func_obj['expr'],
                domain=domain,
                color=func_obj['color'],
                base_step=step_size,
                line_thickness=func_obj['thick'],
                label_text=lbl
            )

            # 2. Analyse and Plot Features
            analyser = MathAnalyser(func_obj['expr'])

            show_endpoints = func_obj['use_custom_domain'] and (
                        func_obj['dom_start_style'] != "None" or func_obj['dom_end_style'] != "None")
            ep_styles = (
                func_obj.get('dom_start_style', 'None').lower(),
                func_obj.get('dom_end_style', 'None').lower()
            )

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

    # Top Control Row
    st.subheader("Preview")

    # Scale Choice for PNG - Hardcoded
    scale_choice = 10

    # Render Interactive Graph
    render_interactive_graph(
        svg_string,
        engine.width_pixels,
        engine.height_pixels,
        target_width_cm,
        target_height_cm,
        scale_choice
    )