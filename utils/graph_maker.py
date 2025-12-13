import math
from fractions import Fraction
import re
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Any, Callable, Optional
import svgwrite
import sympy as sp
import numpy as np
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, \
    convert_xor

# Ensure this import works relative to the utils package
try:
    from .text_renderer import TexEngine
except ImportError:
    from text_renderer import TexEngine


# --- 1. Configuration & Defaults ---
@dataclass
class GraphConfig:
    file_name: str = "Graph"
    grid_cols: Tuple[int, int] = (10, 10)
    grid_scale: Tuple[float, float] = (1.0, 1.0)
    axis_pos: Tuple[int, int] = (0, 0)
    axis_labels: Tuple[str, str] = ("x", "y")

    tick_rounding: Tuple[int, int] = (0, 0)
    minor_per_major: Tuple[int, int] = (5, 5)
    font_family: str = "Times New Roman"
    font_size: int = 11

    grid_thickness_major: float = 0.75
    grid_thickness_minor: float = 0.25
    axis_thickness: float = 1.5
    minor_spacing: Tuple[float, float] = (20.0, 20.0)

    # Grid Visibility Controls
    show_minor_grid: bool = True
    show_major_grid: bool = True
    show_vertical_grid: bool = True
    show_horizontal_grid: bool = True

    # Axis Visibility
    show_x_axis: bool = True
    show_y_axis: bool = True
    show_x_numbers: bool = True
    show_y_numbers: bool = True
    show_x_ticks: bool = True
    show_y_ticks: bool = True

    # Arrows
    show_x_arrow: bool = True
    show_y_arrow: bool = True

    # Aesthetic Controls
    show_label_background: bool = True
    label_background_opacity: float = 0.85
    show_border: bool = False
    show_whisker_caps: bool = True

    # New: Rotated Y Label
    rotate_y_label: bool = False

    # Manual Calibration Offsets (Pixels)
    offset_box_label_y: float = 0.0
    offset_xaxis_num_y: float = 0.0
    offset_xaxis_label_y: float = 0.0
    offset_yaxis_label_x: float = 0.0
    offset_yaxis_label_y: float = 0.0

    force_external_margins: bool = False
    x_label_pos: str = "bottom"
    y_label_pos: str = "side_horizontal"

    pi_x_axis: bool = False
    pi_y_axis: bool = False

    show_zero_label: bool = True

    @property
    def pixels_per_unit_x(self) -> float:
        return (self.minor_spacing[0] * self.minor_per_major[0]) / self.grid_scale[0]

    @property
    def pixels_per_unit_y(self) -> float:
        return (self.minor_spacing[1] * self.minor_per_major[1]) / self.grid_scale[1]


def format_pi_value(val: float) -> str:
    r"""Converts a float to a LaTeX pi fraction string (e.g. 1.57 -> \frac{\pi}{2})."""
    if abs(val) < 1e-9:
        return "0"

    # Determine the coefficient of pi
    coeff = val / math.pi
    frac = Fraction(coeff).limit_denominator(100)

    num = frac.numerator
    den = frac.denominator

    # Build LaTeX string
    if den == 1:
        if num == 1: return r"\pi"
        if num == -1: return r"-\pi"
        return f"{num}" + r"\pi"
    else:
        # Denominator exists
        if num == 1:
            base = r"\pi"
        elif num == -1:
            base = r"-\pi"
        else:
            base = f"{num}" + r"\pi"
        return r"\frac{" + base + r"}{" + str(den) + r"}"

# --- 3. The Graph Engine ---
class GraphEngine:
    def __init__(self, config: GraphConfig = GraphConfig()):
        self.cfg = config
        self.tex_engine = TexEngine()

        self.num_major_x = int(self.cfg.grid_cols[0])
        self.num_major_y = int(self.cfg.grid_cols[1])

        self.idx_xaxis = int(self.cfg.axis_pos[0])
        self.idx_yaxis = int(self.cfg.axis_pos[1])

        self.tick_h = 7

        # --- DYNAMIC MARGIN CALCULATION ---
        extra_bottom = 30 if self.cfg.axis_labels[0] else 0
        # Add extra left margin if rotating Y label or if shifted manually
        extra_left = 0
        if self.cfg.axis_labels[1]:
            if self.cfg.rotate_y_label:
                extra_left = 20
            else:
                # Horizontal label on the left needs more space
                label_w, _ = self.tex_engine.measure(self.cfg.axis_labels[1], self.cfg.font_size)
                extra_left = label_w + 10

        x_label_w, x_label_h = self.tex_engine.measure(self.cfg.axis_labels[0], self.cfg.font_size)
        self.margin_right = max(40.0, x_label_w + 35.0)

        y_label_w, y_label_h = self.tex_engine.measure(self.cfg.axis_labels[1], self.cfg.font_size)
        self.margin_top = max(40.0, y_label_h + 35.0)

        self.margin_left = 40.0 + extra_left
        self.margin_bottom = 40.0 + extra_bottom

        self.grid_width = self.cfg.minor_spacing[0] * self.cfg.minor_per_major[0] * self.num_major_x
        self.grid_height = self.cfg.minor_spacing[1] * self.cfg.minor_per_major[1] * self.num_major_y

        self.width_pixels = self.margin_left + self.grid_width + self.margin_right
        self.height_pixels = self.margin_top + self.grid_height + self.margin_bottom

        self.origin_x = self.margin_left + (self.cfg.minor_spacing[0] * self.cfg.minor_per_major[0] * self.idx_yaxis)
        self.origin_y = self.margin_top + (self.cfg.minor_spacing[1] * self.cfg.minor_per_major[1] * self.idx_xaxis)

        self.dwg = svgwrite.Drawing(size=("100%", "100%"), viewBox=f"0 0 {self.width_pixels} {self.height_pixels}")

        self.clip_id = "grid_clip"
        clip = self.dwg.clipPath(id=self.clip_id)
        clip.add(self.dwg.rect(insert=(self.margin_left, self.margin_top), size=(self.grid_width, self.grid_height)))
        self.dwg.defs.add(clip)

    def math_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        px = self.origin_x + (x * self.cfg.pixels_per_unit_x)
        py = self.origin_y - (y * self.cfg.pixels_per_unit_y)
        return px, py

    def render_text_tex_lite(self, x: float, y: float, text: str, anchor="start", color="black", italic=False,
                             alignment_baseline="auto", font_size=None, container=None, rotation=0):
        if font_size is None:
            font_size = self.cfg.font_size

        box = self.tex_engine.parse_layout(text, font_size=font_size)

        start_x = x
        if anchor == "middle":
            start_x -= box.width / 2
        elif anchor == "end":
            start_x -= box.width

        if box.left_overflow > 0:
            start_x += box.left_overflow

        target = container if container else self.dwg

        # Handle Rotation
        if rotation != 0:
            # Create a group for rotation
            rot_group = self.dwg.g(transform=f"rotate({rotation}, {x}, {y})")
            target.add(rot_group)
            target = rot_group  # Draw text into the rotated group

        box.is_math = italic
        box.render(self.dwg, start_x, y, color, container=target)

    def _draw_arrowhead(self, x, y, direction="right"):
        length = 12
        width = 12
        half_w = width / 2
        if direction == "right":
            points = [(x + length, y), (x, y - half_w), (x, y + half_w)]
        elif direction == "up":
            points = [(x, y - length), (x - half_w, y), (x + half_w, y)]
        else:
            return
        self.dwg.add(self.dwg.polygon(points=points, fill="black"))

    def _format_number(self, val: float, decimals: int) -> str:
        if abs(val) < 1e-10: val = 0.0
        if abs(val - round(val)) < 1e-9:
            return f"{int(round(val))}"
        return f"{val:.{decimals}f}"

    def draw_grid_lines(self):
        c = self.cfg
        x_start, x_end = self.margin_left, self.margin_left + self.grid_width
        y_start, y_end = self.margin_top, self.margin_top + self.grid_height

        if c.show_border:
            self.dwg.add(self.dwg.rect(insert=(x_start, y_start),
                                       size=(self.grid_width, self.grid_height),
                                       fill="none", stroke="black", stroke_width=c.grid_thickness_major))

        if c.show_vertical_grid:
            for i in range(self.num_major_x * c.minor_per_major[0] + 1):
                px = x_start + i * c.minor_spacing[0]
                is_major = (i % c.minor_per_major[0] == 0)

                should_draw = c.show_major_grid if is_major else c.show_minor_grid
                if should_draw:
                    if c.show_border and (i == 0 or i == self.num_major_x * c.minor_per_major[0]):
                        continue
                    width = c.grid_thickness_major if is_major else c.grid_thickness_minor
                    self.dwg.add(
                        self.dwg.line(start=(px, y_start), end=(px, y_end), stroke='black', stroke_width=width))

                if c.show_x_ticks and is_major and i != self.idx_yaxis * c.minor_per_major[0]:
                    if c.show_x_axis:
                        self.dwg.add(self.dwg.line(start=(px, self.origin_y - self.tick_h),
                                                   end=(px, self.origin_y + self.tick_h), stroke='black',
                                                   stroke_width=c.axis_thickness))
                    elif c.show_border:
                        self.dwg.add(self.dwg.line(start=(px, y_end - self.tick_h), end=(px, y_end), stroke='black',
                                                   stroke_width=c.axis_thickness))

        if c.show_horizontal_grid:
            for i in range(self.num_major_y * c.minor_per_major[1] + 1):
                py = y_start + i * c.minor_spacing[1]
                is_major = (i % c.minor_per_major[1] == 0)

                should_draw = c.show_major_grid if is_major else c.show_minor_grid
                if should_draw:
                    if c.show_border and (i == 0 or i == self.num_major_y * c.minor_per_major[1]):
                        continue
                    width = c.grid_thickness_major if is_major else c.grid_thickness_minor
                    self.dwg.add(
                        self.dwg.line(start=(x_start, py), end=(x_end, py), stroke='black', stroke_width=width))

                if c.show_y_ticks and is_major and i != self.idx_xaxis * c.minor_per_major[1]:
                    self.dwg.add(
                        self.dwg.line(start=(self.origin_x - self.tick_h, py), end=(self.origin_x + self.tick_h, py),
                                      stroke='black', stroke_width=c.axis_thickness))

        if c.show_y_axis:
            y_axis_top = y_start - 15 if c.show_y_arrow else y_start
            self.dwg.add(self.dwg.line(start=(self.origin_x, y_axis_top), end=(self.origin_x, y_end), stroke='black',
                                       stroke_width=c.axis_thickness))
            if c.show_y_arrow:
                self._draw_arrowhead(self.origin_x, y_axis_top, direction="up")

        if c.show_x_axis:
            x_axis_right = x_end + 15 if c.show_x_arrow else x_end
            self.dwg.add(
                self.dwg.line(start=(x_start - 10, self.origin_y), end=(x_axis_right, self.origin_y), stroke='black',
                              stroke_width=c.axis_thickness))
            if c.show_x_arrow:
                self._draw_arrowhead(x_axis_right, self.origin_y, direction="right")

    def draw_axis_labels(self):
        c = self.cfg
        x_start, x_end = self.margin_left, self.margin_left + self.grid_width
        y_start, y_end = self.margin_top, self.margin_top + self.grid_height

        # X Numbers
        if c.show_x_numbers:
            for i in range(self.num_major_x * c.minor_per_major[0] + 1):
                is_major = (i % c.minor_per_major[0] == 0)
                if is_major:
                    px = self.margin_left + i * c.minor_spacing[0]
                    # Only skip origin Y if x-axis is crossing y-axis.
                    if c.show_y_axis and i == self.idx_yaxis * c.minor_per_major[0]:
                        pass

                    math_val = (i / c.minor_per_major[0] - self.idx_yaxis) * c.grid_scale[0]

                    if not c.show_zero_label and abs(math_val) < 1e-9:
                        continue

                    if c.pi_x_axis:
                        label = format_pi_value(math_val)
                    else:
                        label = self._format_number(math_val, c.tick_rounding[0])

                    if c.show_x_axis:
                        num_y = self.origin_y + 20
                    else:
                        num_y = y_end + 5 + c.offset_xaxis_num_y

                    # Use parse_layout to get exact ascent/descent for fractions
                    box = self.tex_engine.parse_layout(label, c.font_size)

                    # Draw rect based on actual text ascent (top) and total height
                    self.dwg.add(self.dwg.rect(
                        insert=(px - box.width / 2, num_y - box.ascent),
                        size=(box.width, box.height),
                        fill='white'
                    ))

                    self.render_text_tex_lite(px, num_y, label, anchor="middle")

        # Y Numbers
        if c.show_y_axis and c.show_y_numbers:
            for i in range(self.num_major_y * c.minor_per_major[1] + 1):
                is_major = (i % c.minor_per_major[1] == 0)
                if is_major and (i != self.idx_xaxis * c.minor_per_major[1] or not c.show_x_axis):
                    py = self.margin_top + i * c.minor_spacing[1]
                    math_val = (self.idx_xaxis - i / c.minor_per_major[1]) * c.grid_scale[1]
                    if c.pi_y_axis:
                        label = format_pi_value(math_val)
                    else:
                        label = self._format_number(math_val, c.tick_rounding[1])
                    box = self.tex_engine.parse_layout(label, c.font_size)

                    # Text is drawn at (py + 4), so top of rect is (py + 4) - ascent
                    base_y = py + 4
                    self.dwg.add(self.dwg.rect(
                        insert=(self.origin_x - 10 - box.width, base_y - box.ascent),
                        size=(box.width + 2, box.height),
                        fill='white'
                    ))
                    self.render_text_tex_lite(self.origin_x - 10, py + 4, label, anchor="end")

        # Labels
        # Y Axis Label
        if c.show_y_axis and c.axis_labels[1]:
            if c.rotate_y_label:
                center_y = self.margin_top + (self.grid_height / 2) + c.offset_yaxis_label_y
                left_x = self.margin_left - 35 + c.offset_yaxis_label_x
                self.render_text_tex_lite(left_x, center_y, c.axis_labels[1], anchor="middle", italic=True,
                                          rotation=-90)
            else:
                # RESTORED OLD LOGIC (Top of axis, centered on line)
                y_label_pos = self.margin_top - 32 + c.offset_yaxis_label_y
                pos_x = self.origin_x + c.offset_yaxis_label_x

                self.render_text_tex_lite(pos_x, y_label_pos, c.axis_labels[1], anchor="middle", italic=True)

        # X Axis Label
        is_histogram_style = (not c.show_x_arrow) and (c.show_x_axis)

        if c.show_x_axis and c.axis_labels[0] and not c.show_border:
            if is_histogram_style:
                center_x = self.margin_left + (self.grid_width / 2)
                bottom_y = self.origin_y + 40 + c.offset_xaxis_label_y
                self.render_text_tex_lite(center_x, bottom_y, c.axis_labels[0], anchor="middle", italic=True)
            else:
                x_axis_right = x_end + 15
                x_label_pos = x_axis_right + 12 + 6
                self.render_text_tex_lite(x_label_pos, self.origin_y + 2, c.axis_labels[0], anchor="start", italic=True)

        elif c.axis_labels[0]:
            center_x = self.margin_left + (self.grid_width / 2)
            bottom_y = y_end + 25 + c.offset_xaxis_label_y
            self.render_text_tex_lite(center_x, bottom_y, c.axis_labels[0], anchor="middle", italic=True)

    # --- RESTORED: Function Plotting ---
    def plot_function(self, expr_str: str, domain: Tuple[float, float] = None, color="black", base_step=0.04,
                      line_thickness=1.5, label_text=None):
        if domain is None:
            x_min = -1 * self.cfg.grid_scale[0] * self.idx_yaxis
            x_max = self.cfg.grid_scale[0] * (self.num_major_x - self.idx_yaxis)
            domain = (x_min, x_max)

        x = sp.symbols('x')
        try:
            clean_expr = re.sub(r'^\s*y\s*=\s*', '', expr_str)
            transformations = (standard_transformations + (implicit_multiplication_application, convert_xor))
            expr = parse_expr(clean_expr, transformations=transformations)

            f = sp.lambdify(x, expr, 'math')
            df = sp.lambdify(x, sp.diff(expr, x), 'math')

            singularities = []
            try:
                # 1. Force rewrite of tan/sec/csc/cot to sin/cos to expose the denominator
                expr_rw = expr.rewrite(sp.cos)
                numer, denom = expr_rw.as_numer_denom()

                # 2. Use Numpy to scan for sign changes in denominator (foolproof detection)
                #    If denominator is constant (e.g. 1), we skip this.
                if denom != 1:
                    # Create fast numpy function for denominator
                    f_denom = sp.lambdify(x, denom, modules=['numpy', 'math'])

                    # Scan 1000 points across the screen
                    x_scan = np.linspace(domain[0], domain[1], 1001)
                    y_scan = f_denom(x_scan)

                    # Find indices where sign changes (positive <-> negative)
                    # This indicates a zero-crossing for the denominator (an asymptote)
                    sign_changes = np.where(np.diff(np.sign(y_scan)))[0]

                    for idx in sign_changes:
                        # Use bisection to pinpoint the asymptote location
                        xa, xb = x_scan[idx], x_scan[idx + 1]

                        # Verify it's a crossing (not just touching zero)
                        if f_denom(xa) * f_denom(xb) <= 0:
                            for _ in range(15):  # 15 iterations = high precision
                                mid = (xa + xb) / 2
                                if f_denom(mid) * f_denom(xa) > 0:
                                    xa = mid
                                else:
                                    xb = mid
                            singularities.append((xa + xb) / 2)

                singularities = sorted(singularities)

            except Exception as e:
                print(f"Singularity detection error: {e}")
                pass

        except Exception as e:
            print(f"Error parsing function: {e}")
            return

        step = base_step
        a = domain[0]
        epsilon = 0.05

        path_data = []

        def safe_f(v):
            try:
                val = float(f(v))
                return val if abs(val) < 1e9 else None  # Filter massive infinities
            except:
                return None

        def safe_df(v):
            try:
                return float(df(v))
            except:
                return 0

        def clamp(val, limit=50000):
            return max(-limit, min(limit, val))

        current_seg_started = False
        last_valid_point = None

        while a < domain[1]:
            b = min(a + step, domain[1])
            next_start = b
            segment_break = False

            # Check if we are crossing a known singularity
            for sing in singularities:
                if a <= sing <= b:
                    # Stop just before the asymptote
                    b_stop = sing - epsilon
                    b = max(a, b_stop)  # Ensure we don't go backwards
                    next_start = sing + epsilon
                    segment_break = True
                    break

            if b > a:
                ya, yb = safe_f(a), safe_f(b)
                ma, mb = safe_df(a), safe_df(b)

                if ya is not None and yb is not None:
                    ax_px, ay_px = self.math_to_screen(a, ya)
                    bx_px, by_px = self.math_to_screen(b, yb)

                    if 0 <= bx_px <= self.width_pixels and 0 <= by_px <= self.height_pixels:
                        last_valid_point = (bx_px, by_px)

                    # --- SAFETY CHECK ---
                    # If the line jumps more than 90% of the screen height, BREAK IT.
                    # This hides vertical asymptote lines even if the math detector failed.
                    if abs(ay_px - by_px) < self.height_pixels * 0.9:
                        if not current_seg_started:
                            path_data.append(f"M {ax_px:.2f},{ay_px:.2f}")
                            current_seg_started = True

                        # Bezier smoothing
                        scale_factor = (bx_px - ax_px) / 3.0
                        c1x = ax_px + scale_factor
                        c1y = ay_px - (ma * scale_factor * (self.cfg.pixels_per_unit_y / self.cfg.pixels_per_unit_x))
                        c2x = bx_px - scale_factor
                        c2y = by_px + (mb * scale_factor * (self.cfg.pixels_per_unit_y / self.cfg.pixels_per_unit_x))

                        # Clamp controls to prevent wild loops
                        c1y = clamp(c1y)
                        c2y = clamp(c2y)

                        path_data.append(f"C {c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {bx_px:.2f},{by_px:.2f}")
                    else:
                        current_seg_started = False

            a = next_start
            if segment_break:
                current_seg_started = False

        if path_data:
            # class_="function-layer" allows the auto-cropper to ignore infinity lines
            path = self.dwg.path(d=" ".join(path_data), stroke=color, fill="none", stroke_width=line_thickness,
                                 class_="function-layer")
            path['clip-path'] = f"url(#{self.clip_id})"
            self.dwg.add(path)

            if label_text and last_valid_point:
                lx, ly = last_valid_point
                safe_lbl = re.sub(r'[^a-zA-Z0-9]', '', label_text)
                unique_id = f"lbl_func_{safe_lbl}_{int(lx)}"

                label_group = self.dwg.g(class_="draggable-label", id_=unique_id)
                self.dwg.add(label_group)
                self.render_text_tex_lite(lx + 5, ly, label_text, color=color, anchor="start",
                                          alignment_baseline="middle", container=label_group)


    def draw_box_plots(self, box_stats_list: List[Any], offsets: List[float]):
        start_y = self.margin_top
        box_height = 30

        for i, stats in enumerate(box_stats_list):
            if i >= len(offsets): break

            y_center = start_y + offsets[i]
            y_top = y_center - box_height / 2
            y_bottom = y_center + box_height / 2

            x_min, _ = self.math_to_screen(stats.min_val, 0)
            x_q1, _ = self.math_to_screen(stats.q1, 0)
            x_med, _ = self.math_to_screen(stats.median, 0)
            x_q3, _ = self.math_to_screen(stats.q3, 0)
            x_max, _ = self.math_to_screen(stats.max_val, 0)

            self.dwg.add(self.dwg.line(start=(x_min, y_center), end=(x_q1, y_center), stroke="black", stroke_width=1.5))
            self.dwg.add(self.dwg.line(start=(x_q3, y_center), end=(x_max, y_center), stroke="black", stroke_width=1.5))

            if self.cfg.show_whisker_caps:
                self.dwg.add(self.dwg.line(start=(x_min, y_top + 5), end=(x_min, y_bottom - 5), stroke="black",
                                           stroke_width=1.5))
                self.dwg.add(self.dwg.line(start=(x_max, y_top + 5), end=(x_max, y_bottom - 5), stroke="black",
                                           stroke_width=1.5))

            self.dwg.add(self.dwg.rect(insert=(x_q1, y_top), size=(x_q3 - x_q1, box_height),
                                       fill="white", stroke="black", stroke_width=1.5))

            self.dwg.add(self.dwg.line(start=(x_med, y_top), end=(x_med, y_bottom),
                                       stroke="black", stroke_width=1.5))

            for out in stats.outliers:
                xo, _ = self.math_to_screen(out, 0)
                self.dwg.add(
                    self.dwg.circle(center=(xo, y_center), r=3, fill="white", stroke="black", stroke_width=1.5))

            if stats.label:
                x_label_pos = (x_q1 + x_q3) / 2
                y_label_pos = y_top - 2 + self.cfg.offset_box_label_y

                safe_label = re.sub(r'[^a-zA-Z0-9]', '', stats.label)
                unique_id = f"lbl_box_{safe_label}_{i}"
                label_group = self.dwg.g(class_="draggable-label", id_=unique_id)
                self.dwg.add(label_group)

                if self.cfg.show_label_background:
                    box = self.tex_engine.parse_layout(stats.label, font_size=11)
                    w, h = box.width, box.height
                    padding = 2

                    label_group.add(self.dwg.rect(
                        insert=(x_label_pos - w / 2 - padding, y_label_pos - box.ascent - padding),
                        size=(w + padding * 2, h + padding * 2),
                        fill="white",
                        fill_opacity=str(self.cfg.label_background_opacity)
                    ))

                self.render_text_tex_lite(x_label_pos, y_label_pos, stats.label, anchor="middle", italic=False,
                                          container=label_group)

    def draw_histogram(self, freqs: List[float], start_val=0.0, bin_width=1.0, label_mode="interval"):
        # Calculate pixel width of one bin
        # pixels_per_unit_x is pixels for 1 unit of data.
        # bin_width is how many units wide a bar is.
        bar_width_px = self.cfg.pixels_per_unit_x * bin_width

        if label_mode == "interval":
            y_axis_bottom = self.margin_top + self.grid_height
            edges = [start_val + i * bin_width for i in range(len(freqs) + 1)]
            for i, edge_val in enumerate(edges):
                px, _ = self.math_to_screen(edge_val, 0)

                if self.cfg.show_x_ticks:
                    self.dwg.add(self.dwg.line(start=(px, y_axis_bottom - self.tick_h),
                                               end=(px, y_axis_bottom + self.tick_h),
                                               stroke='black', stroke_width=self.cfg.axis_thickness))

                label = self._format_number(edge_val, self.cfg.tick_rounding[0])
                w, _ = self.tex_engine.measure(label, self.cfg.font_size)
                self.render_text_tex_lite(px, y_axis_bottom + 20 + self.cfg.offset_xaxis_num_y, label, anchor="middle")

        for i, freq in enumerate(freqs):
            left_edge = start_val + i * bin_width
            center_val = left_edge + bin_width / 2
            x_val = center_val
            y_val = freq

            px_center, py_top = self.math_to_screen(x_val, y_val)
            _, py_bottom = self.math_to_screen(x_val, 0)
            h = py_bottom - py_top

            self.dwg.add(self.dwg.rect(insert=(px_center - bar_width_px / 2, py_top), size=(bar_width_px, h),
                                       fill="#e0e0e0", stroke="black", stroke_width=1.2))

            if label_mode == "center":
                label = self._format_number(center_val, self.cfg.tick_rounding[0])
                y_num = py_bottom + 20 + self.cfg.offset_xaxis_num_y
                self.render_text_tex_lite(px_center, y_num, label, anchor="middle")

    def draw_scatter(self, x_data: List[float], y_data: List[float], connect=False, line_of_best_fit=None):
        points = []
        for x, y in zip(x_data, y_data):
            px, py = self.math_to_screen(x, y)
            points.append((px, py))
            self.dwg.add(self.dwg.circle(center=(px, py), r=3.5, fill="black"))

        if connect and len(points) > 1:
            path_d = ["M", f"{points[0][0]},{points[0][1]}"]
            for p in points[1:]:
                path_d.append(f"L {p[0]},{p[1]}")
            self.dwg.add(self.dwg.path(d=" ".join(path_d), stroke="black", fill="none", stroke_width=1.5))

        if line_of_best_fit:
            m, c = line_of_best_fit
            x_min = -1 * self.cfg.grid_scale[0] * self.idx_yaxis
            x_max = self.cfg.grid_scale[0] * (self.num_major_x - self.idx_yaxis)

            y1 = m * x_min + c
            y2 = m * x_max + c

            px1, py1 = self.math_to_screen(x_min, y1)
            px2, py2 = self.math_to_screen(x_max, y2)

            self.dwg.add(self.dwg.line(start=(px1, py1), end=(px2, py2), stroke="black", stroke_width=1.5))

    def draw_features(self, features: List):
        for ft in features:
            px, py = self.math_to_screen(ft.x, ft.y)
            if not (-100 <= px <= self.width_pixels + 100 and -100 <= py <= self.height_pixels + 100):
                continue
            if ft.marker_style == 'filled':
                self.dwg.add(self.dwg.circle(center=(px, py), r=3.5, fill="black", stroke="none"))
            elif ft.marker_style == 'hollow':
                self.dwg.add(self.dwg.circle(center=(px, py), r=3.5, fill="white", stroke="black", stroke_width=1.5))
            elif ft.marker_style == 'cross':
                self.dwg.add(
                    self.dwg.line(start=(px - 3, py - 3), end=(px + 3, py + 3), stroke="black", stroke_width=1.5))
                self.dwg.add(
                    self.dwg.line(start=(px - 3, py + 3), end=(px + 3, py - 3), stroke="black", stroke_width=1.5))

            if ft.label:
                offset_y = 15
                if ft.feature_type == 'stationary':
                    offset_y = -10
                elif ft.feature_type == 'intercept':
                    offset_y = 15

                if py < 50: offset_y = 15

                safe_label = re.sub(r'[^a-zA-Z0-9]', '', ft.label)
                unique_id = f"lbl_{safe_label}_{int(px)}_{int(py)}"
                label_group = self.dwg.g(class_="draggable-label", id_=unique_id)
                self.dwg.add(label_group)

                if self.cfg.show_label_background:
                    box = self.tex_engine.parse_layout(ft.label, font_size=9)
                    w, h = box.width, box.height
                    label_group.add(self.dwg.rect(insert=(px - w / 2 - 2, (py + offset_y) - box.ascent - 2),
                                                  size=(w + 4, h + 4), fill="white",
                                                  fill_opacity=str(self.cfg.label_background_opacity)))
                self.render_text_tex_lite(px, py + offset_y, ft.label, anchor="middle", font_size=9,
                                          container=label_group)

    def get_svg_string(self):
        return self.dwg.tostring()