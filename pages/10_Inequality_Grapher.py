import streamlit as st
import math
import sys
import os
import sympy as sp
import re
import numpy as np
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

# --- SETUP: Path & Imports ---
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.graph_maker import GraphEngine, GraphConfig
from utils.nav import render_sidebar
from utils.interactive_viewer import render_interactive_graph

# --- DATA STRUCTURES ---
class Constraint:
    def __init__(self, func, c_type, style, label, boundary_func=None, line_width=1.5, dash_str=None):
        self.func = func          # The callable function (for y or x comparison)
        self.c_type = c_type      # 'top', 'bot', 'x_max', 'x_min'
        self.style = style        # 'solid', 'dashed'
        self.label = label        # String representation
        self.boundary_func = boundary_func # Function y=f(x) for drawing the line
        self.line_width = line_width
        self.dash_str = dash_str

# --- HELPER: Robust Parser ---
def parse_inequalities(ineq_str, line_width=1.5, dash_len=10, dash_gap=5):
    """
    Parses an inequality string into a list of Constraint objects, applying styling.
    """
    debug_log = []
    constraints = []
    
    if not ineq_str or not ineq_str.strip():
        return constraints, debug_log

    # 1. Regex Split to preserve operators
    parts = re.split(r'\s*(<=|>=|<|>)\s*', ineq_str)
    
    simple_ineqs = []
    if len(parts) >= 3:
        for i in range(1, len(parts), 2):
            lhs = parts[i-1]
            op = parts[i]
            rhs = parts[i+1]
            simple_ineqs.append({'lhs': lhs, 'op': op, 'rhs': rhs})
    else:
        simple_ineqs.append({'lhs': ineq_str, 'op': '', 'rhs': ''})

    x, y = sp.symbols('x y')
    transformations = (standard_transformations + (implicit_multiplication_application, convert_xor))

    for item in simple_ineqs:
        lhs_str, op, rhs_str = item['lhs'], item['op'], item['rhs']
        full_str = f"{lhs_str} {op} {rhs_str}"
        
        style = 'dashed' if op in ['<', '>'] else 'solid'
        
        # Calculate dash string based on user input
        current_dash_str = None
        if style == 'dashed':
            current_dash_str = f"{dash_len},{dash_gap}"
        
        try:
            lhs_expr = parse_expr(lhs_str, transformations=transformations)
            rhs_expr = parse_expr(rhs_str, transformations=transformations)
            equation = lhs_expr - rhs_expr
            
            # 1. Try Solving for Y
            y_sols = sp.solve(equation, y)
            
            if y_sols:
                boundary_y = y_sols[0]
                f_boundary = sp.lambdify(x, boundary_y, modules=['numpy', 'math'])
                
                # Determine Direction (Top vs Bot)
                test_x = 0.0
                try: test_y_base = float(f_boundary(test_x))
                except: 
                    test_x = 1.0
                    try: test_y_base = float(f_boundary(test_x))
                    except: test_y_base = 0.0 
                
                test_y_above = test_y_base + 2.0
                
                check_ineq = None
                if op == '<': check_ineq = lhs_expr.subs({x: test_x, y: test_y_above}) < rhs_expr.subs({x: test_x, y: test_y_above})
                elif op == '>': check_ineq = lhs_expr.subs({x: test_x, y: test_y_above}) > rhs_expr.subs({x: test_x, y: test_y_above})
                elif op == '<=': check_ineq = lhs_expr.subs({x: test_x, y: test_y_above}) <= rhs_expr.subs({x: test_x, y: test_y_above})
                elif op == '>=': check_ineq = lhs_expr.subs({x: test_x, y: test_y_above}) >= rhs_expr.subs({x: test_x, y: test_y_above})
                
                c_type = 'bot' if check_ineq else 'top'
                
                constraints.append(Constraint(
                    func=f_boundary, 
                    c_type=c_type, 
                    style=style, 
                    label=full_str,
                    boundary_func=f_boundary,
                    line_width=line_width,
                    dash_str=current_dash_str
                ))
                continue

            # 2. Try Solving for X
            x_sols = sp.solve(equation, x)
            if x_sols:
                boundary_x = float(x_sols[0])
                test_val_x = boundary_x + 1.0
                
                check_ineq = None
                if op == '<': check_ineq = lhs_expr.subs({x: test_val_x, y: 0}) < rhs_expr.subs({x: test_val_x, y: 0})
                elif op == '>': check_ineq = lhs_expr.subs({x: test_val_x, y: 0}) > rhs_expr.subs({x: test_val_x, y: 0})
                elif op == '<=': check_ineq = lhs_expr.subs({x: test_val_x, y: 0}) <= rhs_expr.subs({x: test_val_x, y: 0})
                elif op == '>=': check_ineq = lhs_expr.subs({x: test_val_x, y: 0}) >= rhs_expr.subs({x: test_val_x, y: 0})

                c_type = 'x_min' if check_ineq else 'x_max'
                
                constraints.append(Constraint(
                    func=boundary_x,
                    c_type=c_type, 
                    style=style, 
                    label=full_str,
                    boundary_func=None,
                    line_width=line_width,
                    dash_str=current_dash_str 
                ))
                continue

        except Exception as e:
            debug_log.append(f"Error parsing part '{full_str}': {e}")

    return constraints, debug_log


# --- ENGINE EXTENSION: PATTERNS & FILL ---
class InequalityGraphEngine(GraphEngine):
    
    def get_viewport_domain(self):
        """
        Calculates the exact domain (x_min, x_max) of the visible grid pixels.
        This fixes the bug where shading stops at the default -5/5 range.
        """
        p_start = self.margin_left
        p_end = self.margin_left + self.grid_width
        
        x_min = (p_start - self.origin_x) / self.cfg.pixels_per_unit_x
        x_max = (p_end - self.origin_x) / self.cfg.pixels_per_unit_x
        
        return (x_min - 0.1, x_max + 0.1)

    def add_dynamic_pattern(self, pattern_type):
        """
        Generates dense, solid black patterns.
        """
        if pattern_type == "Solid":
            return None # Use standard fill color
            
        pid = f"pat_{pattern_type}_black_dense"
        
        if pattern_type == "Stripes":
            pattern = self.dwg.pattern(id=pid, size=(6, 6), patternUnits="userSpaceOnUse", patternTransform="rotate(45)")
            pattern.add(self.dwg.rect(insert=(0,0), size=(6,6), fill="white", fill_opacity=0.0))
            pattern.add(self.dwg.line(start=(0,0), end=(0,6), stroke="black", stroke_width=1.5, stroke_opacity=1.0))
            self.dwg.defs.add(pattern)
            
        elif pattern_type == "Checkers":
            pattern = self.dwg.pattern(id=pid, size=(10, 10), patternUnits="userSpaceOnUse")
            pattern.add(self.dwg.rect(insert=(0,0), size=(5,5), fill="black", fill_opacity=1.0))
            pattern.add(self.dwg.rect(insert=(5,5), size=(5,5), fill="black", fill_opacity=1.0))
            self.dwg.defs.add(pattern)
            
        elif pattern_type == "Dots":
            pattern = self.dwg.pattern(id=pid, size=(8, 8), patternUnits="userSpaceOnUse")
            pattern.add(self.dwg.circle(center=(4,4), r=1.5, fill="black", fill_opacity=1.0))
            self.dwg.defs.add(pattern)
            
        return f"url(#{pid})"

    def draw_feasible_region(self, constraints, color="#3366cc", opacity=0.3, pattern_type="Solid"):
        x_start, x_end = self.get_viewport_domain()
        
        for c in constraints:
            if c.c_type == 'x_min':
                x_start = max(x_start, c.func)
            elif c.c_type == 'x_max':
                x_end = min(x_end, c.func)
        
        if x_start >= x_end:
            return

        step = 0.05
        x_vals = np.arange(x_start, x_end + step/2, step) 
        if len(x_vals) == 0: return

        top_points = []
        bot_points = []
        
        screen_y_min_limit = self.margin_top
        screen_y_max_limit = self.margin_top + self.grid_height

        for xv in x_vals:
            curr_y_min_math = -99999.0 
            curr_y_max_math = 99999.0
            
            for c in constraints:
                if c.c_type == 'top':
                    try:
                        val = float(c.func(xv))
                        curr_y_max_math = min(curr_y_max_math, val)
                    except: pass
                elif c.c_type == 'bot':
                    try:
                        val = float(c.func(xv))
                        curr_y_min_math = max(curr_y_min_math, val)
                    except: pass
            
            if curr_y_max_math < curr_y_min_math:
                continue 
                
            px, _ = self.math_to_screen(xv, 0)
            
            # Handle infinity for Y
            if curr_y_max_math > 1000: py_top = screen_y_min_limit
            else: _, py_top = self.math_to_screen(xv, curr_y_max_math)
                
            if curr_y_min_math < -1000: py_bot = screen_y_max_limit
            else: _, py_bot = self.math_to_screen(xv, curr_y_min_math)
            
            # Clamp to grid box
            py_top = max(screen_y_min_limit, min(screen_y_max_limit, py_top))
            py_bot = max(screen_y_min_limit, min(screen_y_max_limit, py_bot))
            
            if abs(py_bot - py_top) > 0.1:
                top_points.append((px, py_top))
                bot_points.append((px, py_bot))

        if not top_points: return

        path_d = [f"M {top_points[0][0]:.2f},{top_points[0][1]:.2f}"]
        for p in top_points[1:]:
            path_d.append(f"L {p[0]:.2f},{p[1]:.2f}")
        
        path_d.append(f"L {bot_points[-1][0]:.2f},{bot_points[-1][1]:.2f}")
        for p in reversed(bot_points[:-1]):
            path_d.append(f"L {p[0]:.2f},{p[1]:.2f}")
        path_d.append("Z")

        if pattern_type != "Solid":
            fill_val = self.add_dynamic_pattern(pattern_type)
            fill_op = 1.0 
        else:
            fill_val = color
            fill_op = opacity

        region = self.dwg.path(d=" ".join(path_d), fill=fill_val, stroke="none", 
                               fill_opacity=fill_op, class_="inequality-fill")
        region['clip-path'] = f"url(#{self.clip_id})"
        self.dwg.add(region)

    def draw_constraint_lines(self, constraints, domain_x):
        step = 0.05
        x_start, x_end = self.get_viewport_domain()
        x_vals = np.arange(x_start, x_end + step/2, step)
        
        # --- AUTO-CROP FIX ---
        # We calculate limits that are strictly just outside the grid (buffer of 5px).
        # This prevents the SVG bounding box from exploding due to "infinity" points,
        # ensuring the Auto-Fit algorithm crops tightly to the axis area.
        # The clip-path handles the actual visual cutting.
        y_visual_min = self.margin_top
        y_visual_max = self.margin_top + self.grid_height
        
        y_clamp_min = y_visual_min - 5
        y_clamp_max = y_visual_max + 5
        
        for c in constraints:
            line_kwargs = {
                "fill": "none",
                "stroke": "black",
                "stroke_width": c.line_width
            }
            if c.style == 'dashed' and c.dash_str:
                line_kwargs["stroke_dasharray"] = c.dash_str
            
            if c.boundary_func:
                pts = []
                for xv in x_vals:
                    try:
                        yv = float(c.boundary_func(xv))
                        # Basic infinity check
                        if abs(yv) < 1e9:
                            px, py = self.math_to_screen(xv, yv)
                            
                            # CLAMP Y to keep bounding box sane
                            py = max(y_clamp_min, min(y_clamp_max, py))
                            
                            pts.append(f"{px:.2f},{py:.2f}")
                    except: pass
                
                if pts:
                    path_str = "M " + " L ".join(pts)
                    line = self.dwg.path(d=path_str, **line_kwargs)
                    line['clip-path'] = f"url(#{self.clip_id})"
                    self.dwg.add(line)

            elif c.c_type in ['x_min', 'x_max']:
                px, _ = self.math_to_screen(c.func, 0)
                # Draw vertical lines strictly within clamp limits
                line = self.dwg.line(start=(px, y_clamp_min), end=(px, y_clamp_max), **line_kwargs)
                line['clip-path'] = f"url(#{self.clip_id})"
                self.dwg.add(line)


# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Inequality Grapher")
render_sidebar()

# --- CSS ---
st.markdown("""
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 3rem !important; padding-bottom: 1rem; } 
        [data-testid="stSidebarUserContent"] { padding-top: 1.5rem; }
        [data-testid="stSidebar"] hr { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; }
        [data-testid="stSidebar"] h1 { padding-top: 0rem !important; margin-top: 0rem !important; font-size: 1.8rem; }
        div[data-testid="column"] { padding: 0px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: Grid Settings ---
st.sidebar.title("📈 Settings")
st.sidebar.header("Grid")

mode_grid = st.sidebar.radio("Grid Mode", ["Min/Max Window", "Range & Center"], horizontal=True)

# Defaults
scale_x = 1.0; scale_y = 1.0
minor_spacing_x = 10.0; minor_spacing_y = 10.0
target_width_cm = 12.0; target_height_cm = 12.0
global_xmin = -10.0; global_xmax = 10.0

if mode_grid == "Min/Max Window":
    st.sidebar.markdown("### Window Limits")
    link_xy = st.sidebar.checkbox("Link X/Y Scale", value=False)
    auto_scale = st.sidebar.checkbox("Auto-pick Grid Scale", value=True)
    
    c_trig1, c_trig2 = st.sidebar.columns(2)
    trig_x = c_trig1.checkbox("Trig X-Axis (π)", value=False)
    trig_y = c_trig2.checkbox("Trig Y-Axis (π)", value=False)
    
    st.sidebar.markdown("### Target Print Size")
    c_dim1, c_dim2 = st.sidebar.columns(2)
    target_width_cm = c_dim1.number_input("Width (cm)", 5.0, 50.0, 12.0, step=0.5)
    target_height_cm = c_dim2.number_input("Height (cm)", 5.0, 50.0, 12.0, step=0.5)
    
    # Axes
    c_x1, c_x2 = st.sidebar.columns(2)
    global_xmin = c_x1.number_input("X Min", value=-5.0, step=1.0)
    global_xmax = c_x2.number_input("X Max", value=5.0, step=1.0)
    c_y1, c_y2 = st.sidebar.columns(2)
    ymin = c_y1.number_input("Y Min", value=-5.0, step=1.0)
    ymax = c_y2.number_input("Y Max", value=5.0, step=1.0)
    
    # Auto Scale Logic
    def calculate_auto_scale_physical(val_min, val_max, size_cm):
        span = val_max - val_min
        if span <= 0: return 1.0
        target_tick_spacing_cm = 2.0
        approx_num_ticks = size_cm / target_tick_spacing_cm
        if approx_num_ticks < 1: approx_num_ticks = 1
        raw_step = span / approx_num_ticks
        power = 10 ** math.floor(math.log10(raw_step))
        base = raw_step / power
        if base < 1.5: step = 1.0 * power
        elif base < 3.5: step = 2.0 * power
        elif base < 7.5: step = 5.0 * power
        else: step = 10.0 * power
        return max(step, 0.1)

    if auto_scale:
        if trig_x: scale_x = math.pi / 2
        else: scale_x = calculate_auto_scale_physical(global_xmin, global_xmax, target_width_cm)
        
        if link_xy: scale_y = scale_x
        else:
            if trig_y: scale_y = math.pi / 2
            else: scale_y = calculate_auto_scale_physical(ymin, ymax, target_height_cm)
    else:
        scale_x = 1.0; scale_y = 1.0 

    # Grid calculations
    width_units = global_xmax - global_xmin
    height_units = ymax - ymin
    
    x_range = max(1, math.ceil(width_units / scale_x))
    y_range = max(1, math.ceil(height_units / scale_y))
    
    axis_x_pos = int(round(-global_xmin / scale_x))
    axis_y_pos = int(round(ymax / scale_y))

    target_width_pts = target_width_cm * 28.3465
    target_height_pts = target_height_cm * 28.3465
    
    if x_range > 0: minor_spacing_x = target_width_pts / (x_range * 5)
    if y_range > 0: minor_spacing_y = target_height_pts / (y_range * 5)

else:
    # Range & Center Mode
    c1, c2 = st.sidebar.columns(2)
    x_range = c1.slider("X Range", 5, 50, 10)
    y_range = c2.slider("Y Range", 5, 50, 10)
    
    trig_x = False; trig_y = False 
    
    global_xmin = -x_range / 2.0
    global_xmax = x_range / 2.0
    ymin = -y_range / 2.0
    ymax = y_range / 2.0
    
    scale_x = 1.0; scale_y = 1.0
    axis_x_pos = x_range / 2
    axis_y_pos = y_range / 2
    minor_spacing_x = 20.0; minor_spacing_y = 20.0 
    
    target_width_pts = target_width_cm * 28.3465
    target_height_pts = target_height_cm * 28.3465
    minor_spacing_x = target_width_pts / (x_range * 5)
    minor_spacing_y = target_height_pts / (y_range * 5)

st.sidebar.markdown("### Axis Labels")
c_lbl1, c_lbl2 = st.sidebar.columns(2)
label_x = c_lbl1.text_input("X Label", "x")
label_y = c_lbl2.text_input("Y Label", "y")


# --- MAIN INTERFACE ---
col_inputs, col_preview = st.columns([2, 3])

if 'regions_data' not in st.session_state:
    st.session_state.regions_data = [
        {'ineq_str': '1 < x + y <= 4', 'color': "#000000", 'active': True, 
         'opacity': 0.15, 'pattern': 'Solid',
         'line_width': 1.5, 'dash_len': 10.0, 'dash_gap': 5.0}
    ]

def add_region():
    st.session_state.regions_data.append({
        'ineq_str': '', 'color': '#000000', 'active': True, 
        'opacity': 0.15, 'pattern': 'Solid',
        'line_width': 1.5, 'dash_len': 10.0, 'dash_gap': 5.0
    })

def remove_region(idx):
    st.session_state.regions_data.pop(idx)

with col_inputs:
    st.subheader("Inequality System")
    
    intersect_mode = st.checkbox("Intersect All Regions (Find Feasible Region)", value=False)
    
    global_opacity = 0.15
    if intersect_mode:
        st.info("Combined Mode: Intersects active regions.")
        global_opacity = st.slider("Global Opacity", 0.0, 1.0, 0.4, step=0.1)
    else:
        st.info("Independent Mode: Layers separate regions.")

    for i, reg in enumerate(st.session_state.regions_data):
        with st.expander(f"Constraint {i+1}", expanded=True):
            reg['ineq_str'] = st.text_input("Inequality", reg.get('ineq_str', ''), key=f"ineq_{i}", 
                                            placeholder="e.g. y > x or x^2 + y^2 < 9")
            
            c1, c2, c3 = st.columns([1, 1, 1])
            reg['color'] = c1.color_picker("Color", reg['color'], key=f"col_{i}")
            reg['active'] = c2.checkbox("Active", reg.get('active', True), key=f"act_{i}")
            
            # Opacity & Pattern (Only in independent mode)
            if not intersect_mode:
                c4, c5 = st.columns(2)
                reg['opacity'] = c4.slider("Opacity", 0.0, 1.0, reg.get('opacity', 0.2), key=f"op_{i}")
                reg['pattern'] = c5.selectbox("Fill Style", ["Solid", "Stripes", "Checkers", "Dots"], 
                                              index=["Solid", "Stripes", "Checkers", "Dots"].index(reg.get('pattern', 'Solid')),
                                              key=f"pat_{i}")

            # Line Styles
            with st.expander("Line Style", expanded=False):
                c_w, c_dl, c_dg = st.columns(3)
                reg['line_width'] = c_w.number_input("Thickness", 0.5, 10.0, reg.get('line_width', 1.5), step=0.5, key=f"lw_{i}")
                reg['dash_len'] = c_dl.number_input("Dash Len", 1.0, 50.0, reg.get('dash_len', 10.0), step=1.0, key=f"dl_{i}")
                reg['dash_gap'] = c_dg.number_input("Dash Gap", 1.0, 50.0, reg.get('dash_gap', 5.0), step=1.0, key=f"dg_{i}")
            
            if c3.button("🗑️", key=f"del_{i}"):
                remove_region(i)
                st.rerun()

    if st.button("➕ Add Inequality"):
        add_region()
        st.rerun()

with col_preview:
    st.subheader("Preview")
    
    config = GraphConfig(
        grid_cols=(x_range, y_range),
        grid_scale=(scale_x, scale_y),
        axis_pos=(axis_y_pos, axis_x_pos),
        axis_labels=(label_x, label_y),
        minor_spacing=(minor_spacing_x, minor_spacing_y),
        show_minor_grid=True,
        show_major_grid=True,
        pi_x_axis=trig_x,
        pi_y_axis=trig_y
    )
    
    engine = InequalityGraphEngine(config)
    engine.draw_grid_lines()
    engine.draw_axis_labels()
    
    if intersect_mode:
        all_constraints = []
        final_color = "#3366cc"
        final_pattern = "Solid"
        
        for reg in st.session_state.regions_data:
            if reg['active'] and reg['ineq_str']:
                # Pass style params here
                cons, dbg = parse_inequalities(reg['ineq_str'], 
                                               line_width=reg.get('line_width', 1.5),
                                               dash_len=reg.get('dash_len', 10.0),
                                               dash_gap=reg.get('dash_gap', 5.0))
                all_constraints.extend(cons)
                if final_color == "#3366cc": 
                    final_color = reg['color']
                    final_pattern = reg.get('pattern', 'Solid') 

        if all_constraints:
            engine.draw_feasible_region(all_constraints, color=final_color, 
                                        opacity=global_opacity, pattern_type=final_pattern)
            engine.draw_constraint_lines(all_constraints, (0,0))
            
    else:
        for reg in st.session_state.regions_data:
            if not reg['active'] or not reg['ineq_str']: continue
            
            cons, dbg = parse_inequalities(reg['ineq_str'], 
                                           line_width=reg.get('line_width', 1.5),
                                           dash_len=reg.get('dash_len', 10.0),
                                           dash_gap=reg.get('dash_gap', 5.0))
            if cons:
                op = reg.get('opacity', 0.2)
                pat = reg.get('pattern', 'Solid')
                engine.draw_feasible_region(cons, color=reg['color'], opacity=op, pattern_type=pat)
                engine.draw_constraint_lines(cons, (0,0))

    svg_string = engine.get_svg_string()
    render_interactive_graph(svg_string, engine.width_pixels, engine.height_pixels, 
                             target_width_cm, target_height_cm, 10)