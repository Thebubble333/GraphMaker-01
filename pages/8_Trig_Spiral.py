import streamlit as st
import math
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.graph_maker import GraphConfig
from utils.graph_stats import StatsGraphEngine
from utils.interactive_viewer import render_interactive_graph
from utils.nav import render_sidebar

st.set_page_config(layout="wide", page_title="Trig Domain Spiral")
render_sidebar()

# --- CSS ---
st.markdown("""
    <style>
        header {visibility: hidden;}
        .block-container { padding-top: 2rem !important; }
        div[data-testid="column"] { padding: 0px; }
    </style>
""", unsafe_allow_html=True)

st.title("🌀 Trig Argument Spiral")

# --- SIDEBAR: SETTINGS ---
st.sidebar.title("⚙️ Settings")

# 1. Canvas Dimensions
st.sidebar.markdown("### Canvas")
target_width_cm = st.sidebar.number_input("Width (cm)", 5.0, 50.0, 12.0, step=0.5)
target_height_cm = st.sidebar.number_input("Height (cm)", 5.0, 50.0, 10.0, step=0.5)
w_px = target_width_cm * 28.3465
h_px = target_height_cm * 28.3465

# 2. Spiral Aesthetics
st.sidebar.markdown("### Spiral Styling")
base_radius = st.sidebar.slider("Start Radius", 0.5, 5.0, 1.5, step=0.1, help="Distance from center to start of spiral")
growth_rate = st.sidebar.slider("Growth Rate", 0.05, 1.0, 0.15, step=0.01, help="How fast it spirals out")
samples_per_rev = st.sidebar.slider("Smoothness", 50, 500, 200)

# 3. Colors
col_pos = st.sidebar.color_picker("Positive Domain (>= 0)", "#000000")
col_neg = st.sidebar.color_picker("Negative Domain (< 0)", "#FF0000")
col_sols = st.sidebar.color_picker("Solution Arms", "#0000FF")

# --- MAIN: INPUTS ---
col_input, col_preview = st.columns([1, 2])

with col_input:
    st.subheader("Equation Parameters")
    st.markdown(r"Solving for $\theta$ where $\theta = a + bx$")
    
    # Domain of X
    c1, c2 = st.columns(2)
    x_min_pi = c1.number_input("x min (coeff of π)", -10.0, 10.0, -0.5, step=0.125, help="-0.5 is -π/2")
    x_max_pi = c2.number_input("x max (coeff of π)", -10.0, 10.0, 1.0, step=0.125, help="1.0 is π")
    
    # Argument Transformation (theta = a + bx)
    st.markdown("---")
    st.markdown("**Argument Definition:** $2\\pi - 3x$")
    arg_offset_pi = st.number_input("Offset 'a' (coeff of π)", -10.0, 10.0, 2.0, step=0.25)
    arg_slope = st.number_input("Slope 'b' (coefficient of x)", -10.0, 10.0, -3.0, step=0.5)
    
    # Base Solutions (The terminal arms)
    st.markdown("---")
    st.markdown("**Base Solutions ($0$ to $2\\pi$):**")
    
    # Solution 1
    sc1_a, sc1_b = st.columns([1, 1])
    sol1_pi = sc1_a.number_input("Sol 1 (π coeff)", 0.0, 2.0, 0.66667, step=0.1666)
    sol1_lbl = sc1_b.text_input("Label 1", "2π/3")
    
    # Solution 2
    sc2_a, sc2_b = st.columns([1, 1])
    sol2_pi = sc2_a.number_input("Sol 2 (π coeff)", 0.0, 2.0, 1.33333, step=0.1666)
    sol2_lbl = sc2_b.text_input("Label 2", "4π/3")
    
    show_arms = st.checkbox("Show Terminal Arms", value=True)

# --- LOGIC: CALC RANGE ---
# Convert Inputs to actual radians
x_min = x_min_pi * math.pi
x_max = x_max_pi * math.pi
a = arg_offset_pi * math.pi
b = arg_slope

# Calculate Theta Interval
theta_start = a + b * x_min
theta_end = a + b * x_max

# Ensure start is smaller than end for the loop
t_min = min(theta_start, theta_end)
t_max = max(theta_start, theta_end)

# --- PREVIEW ---
with col_preview:
    st.subheader("Visualisation")
    
    # 1. Setup Graph Engine (Canvas)
    config = GraphConfig(
        grid_cols=(10, 10), 
        show_border=False,
        show_x_axis=False, 
        show_y_axis=False,
        show_vertical_grid=False,
        show_horizontal_grid=False,
        axis_pos=(5, 5) 
    )
    
    engine = StatsGraphEngine(config)
    engine.width_pixels = w_px
    engine.height_pixels = h_px
    engine.dwg['viewBox'] = f"0 0 {w_px} {h_px}"
    
    # Center
    cx = w_px / 2
    cy = h_px / 2
    
    # Scale factor
    unit_px = 60.0 
    
    def polar_to_screen(r, theta_rad):
        # SVG y is down, so we flip sin
        x = cx + r * unit_px * math.cos(theta_rad)
        y = cy - r * unit_px * math.sin(theta_rad)
        return x, y

    # 2. Draw Axes
    axis_len = 4.5 * unit_px
    engine.dwg.add(engine.dwg.line((cx - axis_len, cy), (cx + axis_len, cy), stroke="black", stroke_width=1))
    engine.dwg.add(engine.dwg.line((cx, cy - axis_len), (cx, cy + axis_len), stroke="black", stroke_width=1))

    # 3. Draw Terminal Arms (Infinite Lines) & Labels
    if show_arms:
        arm_len = 4.0
        
        # Helper to draw arm and label
        def draw_arm(angle_pi, label_text):
            angle_rad = angle_pi * math.pi
            ax, ay = polar_to_screen(arm_len, angle_rad)
            engine.dwg.add(engine.dwg.line((cx, cy), (ax, ay), stroke=col_sols, stroke_width=2))
            
            # Label
            if label_text:
                lx, ly = polar_to_screen(arm_len + 0.4, angle_rad)
                # Adjust text anchor based on quadrant for better visibility
                anchor = "middle"
                cos_a = math.cos(angle_rad)
                sin_a = math.sin(angle_rad) # Remember SVG Y is flipped, but for logic:
                
                # Simple offset adjustments
                dx = 0
                dy = 5 # Center vertically roughly
                
                engine.dwg.add(engine.dwg.text(
                    label_text, 
                    insert=(lx + dx, ly + dy), 
                    fill=col_sols, 
                    font_size="16px", 
                    font_family="serif",
                    font_weight="bold",
                    text_anchor="middle"
                ))

        draw_arm(sol1_pi, sol1_lbl)
        draw_arm(sol2_pi, sol2_lbl)

    # 4. Generate Spiral Points (Split by Positive/Negative)
    
    def draw_spiral_segment(start_t, end_t, color, dashed=False):
        if start_t >= end_t: return
        
        # Calculate steps based on arc length
        seg_angle = end_t - start_t
        steps = int(seg_angle / (2*math.pi) * samples_per_rev) + 5
        dt = seg_angle / steps
        
        seg_points = []
        for i in range(steps + 1):
            theta = start_t + i * dt
            # Radius Formula: r based on total distance from t_min of the WHOLE domain
            # We want the spiral to be continuous, so r must depend on (theta - t_min)
            # regardless of whether theta is pos or neg.
            r = base_radius + growth_rate * (theta - t_min)
            px, py = polar_to_screen(r, theta)
            seg_points.append((px, py))
            
        if len(seg_points) > 1:
            path_d = f"M {seg_points[0][0]},{seg_points[0][1]} "
            for p in seg_points[1:]:
                path_d += f"L {p[0]},{p[1]} "
            
            stroke_dash = "4,2" if dashed else "none"
            engine.dwg.add(engine.dwg.path(d=path_d, fill="none", stroke=color, stroke_width=2, stroke_dasharray=stroke_dash))

    # Logic to split at 0
    # Range is [t_min, t_max]
    
    # Segment 1: Negative Part (Red) -> [t_min, 0] (if t_min < 0)
    if t_min < 0:
        end_neg = min(0, t_max)
        draw_spiral_segment(t_min, end_neg, col_neg)
        
    # Segment 2: Positive Part (Black) -> [0, t_max] (if t_max > 0)
    if t_max > 0:
        start_pos = max(0, t_min)
        draw_spiral_segment(start_pos, t_max, col_pos)

    # 5. Start/End Labels (Optional but helpful)
    # Start Label
    r_start = base_radius # r at t_min is base_radius
    sx, sy = polar_to_screen(r_start, t_min)
    engine.dwg.add(engine.dwg.text(
        f"Start ({theta_start/math.pi:.2f}π)", 
        insert=(sx + 10, sy), 
        fill="#666", 
        font_size="10px", 
        font_family="monospace"
    ))

    # 6. Calculate and Draw Intersections (The Dots)
    solutions = [sol1_pi * math.pi, sol2_pi * math.pi]
    dot_radius = 4
    
    # Scan for k
    k_range = range(-10, 10) 
    
    for sol in solutions:
        for k in k_range:
            current_theta = sol + 2 * math.pi * k
            if t_min <= current_theta <= t_max:
                r_dot = base_radius + growth_rate * (current_theta - t_min)
                dx, dy = polar_to_screen(r_dot, current_theta)
                
                # Determine color based on theta
                dot_col = col_neg if current_theta < 0 else col_pos
                
                # Draw Dot
                engine.dwg.add(engine.dwg.circle(center=(dx, dy), r=dot_radius, fill=dot_col))
                engine.dwg.add(engine.dwg.circle(center=(dx, dy), r=dot_radius, fill="none", stroke="black", stroke_width=0.5))

    # Render
    svg = engine.get_svg_string()
    render_interactive_graph(svg, w_px, h_px, target_width_cm, target_height_cm, 10)
    
    st.info(f"**Domain Analysis:**\n\n$x \in [{x_min_pi}\\pi, {x_max_pi}\\pi]$\n\n$\\theta \in [{t_min/math.pi:.2f}\\pi, {t_max/math.pi:.2f}\\pi]$")