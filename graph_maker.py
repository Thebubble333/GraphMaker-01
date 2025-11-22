import math
import re
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Any, Callable, Optional
import svgwrite
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, \
    convert_xor
from text_renderer import TexEngine


# --- 1. Configuration & Defaults ---
@dataclass
class GraphConfig:
    file_name: str = "Graph"
    grid_cols: Tuple[int, int] = (5, 5)
    grid_scale: Tuple[float, float] = (5.0, 5.0)
    axis_pos: Tuple[int, int] = (0, 0)
    axis_labels: Tuple[str, str] = ("x", "y")

    tick_rounding: Tuple[int, int] = (0, 0)
    minor_per_major: Tuple[int, int] = (5, 5)
    font_family: str = "Times New Roman"
    font_size: int = 11

    grid_thickness_major: float = 0.75
    grid_thickness_minor: float = 0.25
    axis_thickness: float = 1.5
    minor_spacing: Tuple[float, float] = (10.0, 10.0)

    show_minor_grid: bool = True
    show_major_grid: bool = True
    show_x_axis: bool = True
    show_y_axis: bool = True
    show_x_numbers: bool = True
    show_y_numbers: bool = True
    show_x_ticks: bool = True
    show_y_ticks: bool = True

    show_label_background: bool = True
    label_background_opacity: float = 0.85

    @property
    def pixels_per_unit_x(self) -> float:
        return (self.minor_spacing[0] * self.minor_per_major[0]) / self.grid_scale[0]

    @property
    def pixels_per_unit_y(self) -> float:
        return (self.minor_spacing[1] * self.minor_per_major[1]) / self.grid_scale[1]


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
        x_label_w, x_label_h = self.tex_engine.measure(self.cfg.axis_labels[0], self.cfg.font_size)
        self.margin_right = max(40.0, x_label_w + 35.0)

        y_label_w, y_label_h = self.tex_engine.measure(self.cfg.axis_labels[1], self.cfg.font_size)
        self.margin_top = max(40.0, y_label_h + 35.0)

        self.margin_left = 40.0
        self.margin_bottom = 40.0

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
                             alignment_baseline="auto", font_size=None, container=None):
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

        # Support rendering into a group if provided
        target = container if container else self.dwg
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
        x_start, x_end = self.margin_left, self.width_pixels - self.margin_right
        y_start, y_end = self.margin_top, self.height_pixels - self.margin_bottom

        for i in range(self.num_major_x * c.minor_per_major[0] + 1):
            px = x_start + i * c.minor_spacing[0]
            is_major = (i % c.minor_per_major[0] == 0)

            if is_major:
                should_draw = c.show_major_grid
            else:
                should_draw = c.show_minor_grid

            if should_draw:
                width = c.grid_thickness_major if is_major else c.grid_thickness_minor
                self.dwg.add(self.dwg.line(start=(px, y_start), end=(px, y_end), stroke='black', stroke_width=width))

            if c.show_x_axis and c.show_x_ticks and is_major and i != self.idx_yaxis * c.minor_per_major[0]:
                self.dwg.add(
                    self.dwg.line(start=(px, self.origin_y - self.tick_h), end=(px, self.origin_y + self.tick_h),
                                  stroke='black', stroke_width=c.axis_thickness))

        for i in range(self.num_major_y * c.minor_per_major[1] + 1):
            py = y_start + i * c.minor_spacing[1]
            is_major = (i % c.minor_per_major[1] == 0)

            if is_major:
                should_draw = c.show_major_grid
            else:
                should_draw = c.show_minor_grid

            if should_draw:
                width = c.grid_thickness_major if is_major else c.grid_thickness_minor
                self.dwg.add(self.dwg.line(start=(x_start, py), end=(x_end, py), stroke='black', stroke_width=width))

            if c.show_y_axis and c.show_y_ticks and is_major and i != self.idx_xaxis * c.minor_per_major[1]:
                self.dwg.add(
                    self.dwg.line(start=(self.origin_x - self.tick_h, py), end=(self.origin_x + self.tick_h, py),
                                  stroke='black', stroke_width=c.axis_thickness))

        if c.show_y_axis:
            y_axis_top = y_start - 15
            self.dwg.add(
                self.dwg.line(start=(self.origin_x, y_axis_top), end=(self.origin_x, y_end + 10), stroke='black',
                              stroke_width=c.axis_thickness))
            self._draw_arrowhead(self.origin_x, y_axis_top, direction="up")

        if c.show_x_axis:
            x_axis_right = x_end + 15
            self.dwg.add(
                self.dwg.line(start=(x_start - 10, self.origin_y), end=(x_axis_right, self.origin_y), stroke='black',
                              stroke_width=c.axis_thickness))
            self._draw_arrowhead(x_axis_right, self.origin_y, direction="right")

    def draw_axis_labels(self):
        c = self.cfg

        if c.show_x_axis and c.show_x_numbers:
            for i in range(self.num_major_x * c.minor_per_major[0] + 1):
                is_major = (i % c.minor_per_major[0] == 0)
                if is_major and i != self.idx_yaxis * c.minor_per_major[0]:
                    px = self.margin_left + i * c.minor_spacing[0]
                    math_val = (i / c.minor_per_major[0] - self.idx_yaxis) * c.grid_scale[0]
                    label = self._format_number(math_val, c.tick_rounding[0])
                    w, _ = self.tex_engine.measure(label, c.font_size)
                    self.dwg.add(self.dwg.rect(insert=(px - w / 2, self.origin_y + 9), size=(w, 12), fill='white'))
                    self.render_text_tex_lite(px, self.origin_y + 20, label, anchor="middle")

        if c.show_y_axis and c.show_y_numbers:
            for i in range(self.num_major_y * c.minor_per_major[1] + 1):
                is_major = (i % c.minor_per_major[1] == 0)
                if is_major and i != self.idx_xaxis * c.minor_per_major[1]:
                    py = self.margin_top + i * c.minor_spacing[1]
                    math_val = (self.idx_xaxis - i / c.minor_per_major[1]) * c.grid_scale[1]
                    label = self._format_number(math_val, c.tick_rounding[1])
                    w, _ = self.tex_engine.measure(label, c.font_size)
                    self.dwg.add(self.dwg.rect(insert=(self.origin_x - 10 - w, py - 6), size=(w + 2, 12), fill='white'))
                    self.render_text_tex_lite(self.origin_x - 10, py + 4, label, anchor="end")

        if c.show_y_axis and c.axis_labels[1]:
            y_label_pos = self.margin_top - 32
            self.render_text_tex_lite(self.origin_x, y_label_pos, c.axis_labels[1], anchor="middle", italic=True)

        if c.show_x_axis and c.axis_labels[0]:
            x_grid_end = self.width_pixels - self.margin_right
            x_axis_right = x_grid_end + 15
            x_label_pos = x_axis_right + 12 + 6
            self.render_text_tex_lite(x_label_pos, self.origin_y + 2, c.axis_labels[0], anchor="start", italic=True)

    def draw_features(self, features: List):
        for ft in features:
            px, py = self.math_to_screen(ft.x, ft.y)

            if not (-100 <= px <= self.width_pixels + 100 and -100 <= py <= self.height_pixels + 100):
                continue

            # Draw Marker (Static)
            if ft.marker_style == 'filled':
                self.dwg.add(self.dwg.circle(center=(px, py), r=3.5, fill="black", stroke="none"))
            elif ft.marker_style == 'hollow':
                self.dwg.add(self.dwg.circle(center=(px, py), r=3.5, fill="white", stroke="black", stroke_width=1.5))
            elif ft.marker_style == 'cross':
                self.dwg.add(
                    self.dwg.line(start=(px - 3, py - 3), end=(px + 3, py + 3), stroke="black", stroke_width=1.5))
                self.dwg.add(
                    self.dwg.line(start=(px - 3, py + 3), end=(px + 3, py - 3), stroke="black", stroke_width=1.5))

            # Draw Label (Draggable)
            if ft.label:
                offset_y = 15
                if ft.feature_type == 'stationary':
                    offset_y = -10
                elif ft.feature_type == 'intercept':
                    offset_y = 15

                if py < 50: offset_y = 15

                # --- UNIQUE ID GENERATION ---
                # We create a deterministic ID based on label content + original position
                # This allows JS to find this element again even after Python regenerates it
                safe_label = re.sub(r'[^a-zA-Z0-9]', '', ft.label)
                unique_id = f"lbl_{safe_label}_{int(px)}_{int(py)}"

                # Use id_ parameter for svgwrite
                label_group = self.dwg.g(class_="draggable-label", id_=unique_id)
                self.dwg.add(label_group)

                font_size_label = 9
                if self.cfg.show_label_background:
                    box = self.tex_engine.parse_layout(ft.label, font_size=font_size_label)
                    w = box.width
                    h = box.height
                    padding = 2

                    rect_x = px - w / 2 - padding
                    rect_y = (py + offset_y) - box.ascent - padding
                    rect_w = w + (padding * 2)
                    rect_h = h + (padding * 2)

                    label_group.add(self.dwg.rect(
                        insert=(rect_x, rect_y),
                        size=(rect_w, rect_h),
                        fill="white",
                        fill_opacity=str(self.cfg.label_background_opacity)
                    ))

                self.render_text_tex_lite(px, py + offset_y, ft.label, anchor="middle", font_size=font_size_label,
                                          color="#333", container=label_group)

    def plot_function(self, expr_str: str, domain: Tuple[float, float] = None, color="black", base_step=0.1,
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
                numer, denom = expr.as_numer_denom()
                sols = sp.solve(denom, x)
                singularities = [float(s) for s in sols if s.is_real]
            except Exception:
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
                return float(f(v))
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

            for sing in singularities:
                if a <= sing <= b:
                    b_stop = sing - epsilon
                    if a >= b_stop:
                        b = b_stop
                    else:
                        b = b_stop
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

                    if abs(ay_px - by_px) < self.height_pixels * 100:
                        if not current_seg_started:
                            path_data.append(f"M {ax_px:.2f},{ay_px:.2f}")
                            current_seg_started = True

                        scale_factor = (bx_px - ax_px) / 3.0
                        c1x = ax_px + scale_factor
                        c1y = ay_px - (ma * scale_factor * (self.cfg.pixels_per_unit_y / self.cfg.pixels_per_unit_x))
                        c2x = bx_px - scale_factor
                        c2y = by_px + (mb * scale_factor * (self.cfg.pixels_per_unit_y / self.cfg.pixels_per_unit_x))
                        c1y = clamp(c1y)
                        c2y = clamp(c2y)
                        path_data.append(f"C {c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {bx_px:.2f},{by_px:.2f}")

            a = next_start
            if segment_break:
                current_seg_started = False

        if path_data:
            path = self.dwg.path(d=" ".join(path_data), stroke=color, fill="none", stroke_width=line_thickness)
            path['clip-path'] = f"url(#{self.clip_id})"
            self.dwg.add(path)

            # --- MAIN LABEL DRAWING LOGIC ---
            if label_text:
                # 1. Calculate Logic Position (Math Coords)
                target_x = 0.0
                target_y = None

                # Try to place near Y-intercept (x=0) if within domain
                if domain[0] <= 0 <= domain[1]:
                    try:
                        val = float(f(0))
                        if math.isfinite(val):
                            target_y = val
                            target_x = 0.0
                    except:
                        pass

                # Fallback: Midpoint of domain if x=0 is invalid or out of view
                if target_y is None:
                    mid_x = (domain[0] + domain[1]) / 2
                    try:
                        val = float(f(mid_x))
                        if math.isfinite(val):
                            target_y = val
                            target_x = mid_x
                    except:
                        pass

                # Determine Screen Coordinates
                px, py = 0, 0
                valid_pos = False
                if target_y is not None:
                    px, py = self.math_to_screen(target_x, target_y)
                    valid_pos = True
                elif last_valid_point:
                    # Last resort: end of the line
                    px, py = last_valid_point
                    valid_pos = True

                if valid_pos:
                    # Offset to avoid covering the line/point
                    offset_x = 15
                    offset_y = -15

                    # Create Draggable Group
                    # ID is based on expression string (e.g. lbl_func_5sinx)
                    safe_label = re.sub(r'[^a-zA-Z0-9]', '', label_text)
                    unique_id = f"lbl_func_{safe_label}"

                    label_group = self.dwg.g(class_="draggable-label", id_=unique_id)
                    self.dwg.add(label_group)

                    # Optional Background Box
                    font_size_label = 12
                    if self.cfg.show_label_background:
                        box = self.tex_engine.parse_layout(label_text, font_size=font_size_label)
                        w = box.width
                        h = box.height
                        padding = 2

                        rect_x = (px + offset_x) - w / 2 - padding
                        rect_y = (py + offset_y) - box.ascent - padding
                        rect_w = w + (padding * 2)
                        rect_h = h + (padding * 2)

                        label_group.add(self.dwg.rect(
                            insert=(rect_x, rect_y),
                            size=(rect_w, rect_h),
                            fill="white",
                            fill_opacity=str(self.cfg.label_background_opacity)
                        ))

                    # Render Text
                    self.render_text_tex_lite(px + offset_x, py + offset_y, label_text,
                                              color=color, anchor="middle",
                                              font_size=font_size_label,
                                              container=label_group)

    def get_svg_string(self):
        return self.dwg.tostring()