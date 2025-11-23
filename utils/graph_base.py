import svgwrite
from dataclasses import dataclass
from typing import Tuple

try:
    from .text_renderer import TexEngine
except ImportError:
    from text_renderer import TexEngine


@dataclass
class GraphConfig:
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

    # Toggles
    show_minor_grid: bool = True
    show_major_grid: bool = True
    show_vertical_grid: bool = True
    show_horizontal_grid: bool = True
    show_x_axis: bool = True
    show_y_axis: bool = True
    show_x_numbers: bool = True
    show_y_numbers: bool = True
    show_x_ticks: bool = True
    show_y_ticks: bool = True
    show_x_arrow: bool = True
    show_y_arrow: bool = True
    show_label_background: bool = True
    label_background_opacity: float = 0.85
    show_border: bool = False
    show_whisker_caps: bool = True

    # New: Force margins to stay wide even if axes are internal
    force_external_margins: bool = False

    # Label Positions
    y_label_pos: str = "top"
    x_label_pos: str = "right"

    # Offsets
    offset_xaxis_num_y: float = 0.0
    offset_xaxis_label_y: float = 0.0
    offset_yaxis_label_x: float = 0.0
    offset_yaxis_label_y: float = 0.0

    # Compatibility
    rotate_y_label: bool = False

    @property
    def pixels_per_unit_x(self) -> float:
        return (self.minor_spacing[0] * self.minor_per_major[0]) / self.grid_scale[0]

    @property
    def pixels_per_unit_y(self) -> float:
        return (self.minor_spacing[1] * self.minor_per_major[1]) / self.grid_scale[1]


class BaseGraphEngine:
    def __init__(self, config: GraphConfig = GraphConfig()):
        self.cfg = config
        self.tex_engine = TexEngine()

        self.num_major_x = int(self.cfg.grid_cols[0])
        self.num_major_y = int(self.cfg.grid_cols[1])
        self.idx_xaxis = int(self.cfg.axis_pos[0])  # Row index where X axis sits (Y=0)
        self.idx_yaxis = int(self.cfg.axis_pos[1])  # Col index where Y axis sits (X=0)
        self.tick_h = 7

        # --- SMART MARGIN CALCULATIONS ---
        # Base padding increased to 35.0 to prevent Y-arrow clipping at top
        pad = 35.0

        # 1. Detect Internal vs External Axes
        # An axis is "Internal" if it is strictly inside the grid (not on edges)
        is_y_axis_internal = (0 < self.idx_yaxis < self.num_major_x)
        is_x_axis_internal = (0 < self.idx_xaxis < self.num_major_y)

        # Override smart detection if forced
        if self.cfg.force_external_margins:
            is_y_axis_internal = False
            is_x_axis_internal = False

        # --- Top Margin ---
        if self.cfg.y_label_pos == "top" and self.cfg.axis_labels[1]:
            # Arrow (approx 30px) + Label (15px) + Padding
            self.margin_top = 65.0
        else:
            self.margin_top = pad

        # --- Bottom Margin ---
        # If X axis is internal, the numbers are inside the grid.
        # We only need space for the label (if bottom) or just padding.
        if self.cfg.x_label_pos == "bottom" and self.cfg.axis_labels[0]:
            # Label needs space regardless
            self.margin_bottom = 55.0
        else:
            # If internal, we don't need space for numbers below the graph
            if is_x_axis_internal and not self.cfg.show_border:
                self.margin_bottom = 15.0  # Minimal padding
            else:
                self.margin_bottom = 35.0  # Space for numbers

        # --- Right Margin ---
        x_label_w, _ = self.tex_engine.measure(self.cfg.axis_labels[0], self.cfg.font_size)
        if self.cfg.x_label_pos == "right" and self.cfg.axis_labels[0]:
            # Arrow (approx 30px) + Label Width + Padding
            self.margin_right = max(pad, 45.0 + x_label_w)
        else:
            self.margin_right = pad

        # --- Left Margin ---
        # If Y axis is internal, numbers are inside.
        extra_left = 0
        if self.cfg.y_label_pos in ["side_horizontal", "side_vertical"] and self.cfg.axis_labels[1]:
            label_w, _ = self.tex_engine.measure(self.cfg.axis_labels[1], self.cfg.font_size)
            # Add extra space for the label itself
            extra_left = label_w + 15

        if is_y_axis_internal and not self.cfg.show_border:
            # Collapsed margin (just enough for label if exists)
            self.margin_left = 15.0 + extra_left
        else:
            # Full margin for numbers
            self.margin_left = pad + extra_left

        # --- GRID & CANVAS SETUP ---
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
        if box.left_overflow > 0: start_x += box.left_overflow
        target = container if container else self.dwg
        if rotation != 0:
            rot_group = self.dwg.g(transform=f"rotate({rotation}, {x}, {y})")
            target.add(rot_group)
            target = rot_group
        box.is_math = italic
        box.render(self.dwg, start_x, y, color, container=target)

    def _format_number(self, val: float, decimals: int) -> str:
        if abs(val) < 1e-10: val = 0.0
        if abs(val - round(val)) < 1e-9:
            return f"{int(round(val))}"
        return f"{val:.{decimals}f}"

    def _draw_arrowhead(self, x, y, direction="right"):
        length, width = 12, 12
        half_w = width / 2
        if direction == "right":
            points = [(x + length, y), (x, y - half_w), (x, y + half_w)]
        elif direction == "up":
            points = [(x, y - length), (x - half_w, y), (x + half_w, y)]
        else:
            return
        self.dwg.add(self.dwg.polygon(points=points, fill="black"))

    def draw_grid_lines(self):
        c = self.cfg
        x_start, x_end = self.margin_left, self.margin_left + self.grid_width
        y_start, y_end = self.margin_top, self.margin_top + self.grid_height

        if c.show_border:
            self.dwg.add(self.dwg.rect(insert=(x_start, y_start), size=(self.grid_width, self.grid_height), fill="none",
                                       stroke="black", stroke_width=c.grid_thickness_major))

        if c.show_vertical_grid:
            for i in range(self.num_major_x * c.minor_per_major[0] + 1):
                px = x_start + i * c.minor_spacing[0]
                is_major = (i % c.minor_per_major[0] == 0)
                should_draw = c.show_major_grid if is_major else c.show_minor_grid
                if should_draw:
                    if c.show_border and (i == 0 or i == self.num_major_x * c.minor_per_major[0]): continue
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
                    if c.show_border and (i == 0 or i == self.num_major_y * c.minor_per_major[1]): continue
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
            if c.show_y_arrow: self._draw_arrowhead(self.origin_x, y_axis_top, direction="up")

        if c.show_x_axis:
            x_axis_right = x_end + 15 if c.show_x_arrow else x_end
            self.dwg.add(
                self.dwg.line(start=(x_start - 10, self.origin_y), end=(x_axis_right, self.origin_y), stroke='black',
                              stroke_width=c.axis_thickness))
            if c.show_x_arrow: self._draw_arrowhead(x_axis_right, self.origin_y, direction="right")

    def draw_axis_labels(self):
        c = self.cfg
        x_start, x_end = self.margin_left, self.margin_left + self.grid_width
        y_start, y_end = self.margin_top, self.margin_top + self.grid_height

        # --- X NUMBERS ---
        if c.show_x_numbers:
            for i in range(self.num_major_x * c.minor_per_major[0] + 1):
                if i % c.minor_per_major[0] == 0:
                    px = self.margin_left + i * c.minor_spacing[0]
                    math_val = (i / c.minor_per_major[0] - self.idx_yaxis) * c.grid_scale[0]
                    label = self._format_number(math_val, c.tick_rounding[0])

                    if c.show_x_axis:
                        base_y = self.origin_y + 20
                    else:
                        base_y = y_end + 5

                    num_y = base_y + c.offset_xaxis_num_y
                    w, _ = self.tex_engine.measure(label, c.font_size)
                    self.dwg.add(self.dwg.rect(insert=(px - w / 2, num_y - 11), size=(w, 12), fill='white'))
                    self.render_text_tex_lite(px, num_y, label, anchor="middle")

        # --- Y NUMBERS ---
        if c.show_y_numbers:
            for i in range(self.num_major_y * c.minor_per_major[1] + 1):
                if i % c.minor_per_major[1] == 0:
                    if (i != self.idx_xaxis * c.minor_per_major[1] or not c.show_x_axis):
                        py = self.margin_top + i * c.minor_spacing[1]
                        math_val = (self.idx_xaxis - i / c.minor_per_major[1]) * c.grid_scale[1]
                        label = self._format_number(math_val, c.tick_rounding[1])
                        w, _ = self.tex_engine.measure(label, c.font_size)

                        base_x = self.origin_x - 10
                        self.dwg.add(self.dwg.rect(insert=(base_x - w, py - 6), size=(w + 2, 12), fill='white'))
                        self.render_text_tex_lite(base_x, py + 4, label, anchor="end")

        # --- Y AXIS LABEL ---
        if c.axis_labels[1]:
            if c.y_label_pos == "top":
                # UPDATED: Move 2px right
                pos_x = self.origin_x + 2 + c.offset_yaxis_label_x
                pos_y = y_start - 40 + c.offset_yaxis_label_y
                self.render_text_tex_lite(pos_x, pos_y, c.axis_labels[1], anchor="middle", italic=True)

            elif c.y_label_pos == "side_horizontal":
                # UPDATED: Check if Y-axis is on the far left (idx_yaxis == 0).
                # If so, move further left (-30) to clear numbers.
                base_offset = -10
                if self.idx_yaxis == 0:
                    base_offset = -30

                pos_x = self.margin_left + base_offset + c.offset_yaxis_label_x
                pos_y = self.margin_top + (self.grid_height / 2) + c.offset_yaxis_label_y
                self.render_text_tex_lite(pos_x, pos_y, c.axis_labels[1], anchor="end", italic=True)

            elif c.y_label_pos == "side_vertical":
                pos_x = self.margin_left - 35 + c.offset_yaxis_label_x
                pos_y = self.margin_top + (self.grid_height / 2) + c.offset_yaxis_label_y
                self.render_text_tex_lite(pos_x, pos_y, c.axis_labels[1], anchor="middle", italic=True, rotation=-90)

        # --- X AXIS LABEL ---
        if c.axis_labels[0]:
            if c.x_label_pos == "bottom":
                pos_x = self.margin_left + (self.grid_width / 2)
                pos_y = y_end + 35 + c.offset_xaxis_label_y
                self.render_text_tex_lite(pos_x, pos_y, c.axis_labels[0], anchor="middle", italic=True)

            else:
                pos_x = x_end + 40 + c.offset_xaxis_label_x if hasattr(c, 'offset_xaxis_label_x') else x_end + 40
                # UPDATED: Move down 15px (2 -> 17)
                pos_y = self.origin_y + 17 + c.offset_xaxis_label_y
                self.render_text_tex_lite(pos_x, pos_y, c.axis_labels[0], anchor="start", italic=True)

    def get_svg_string(self):
        return self.dwg.tostring()