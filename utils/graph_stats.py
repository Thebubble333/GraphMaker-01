import re
from typing import List, Any
from .graph_base import BaseGraphEngine


class StatsGraphEngine(BaseGraphEngine):

    def draw_histogram(self, freqs: List[float], start_val=0.0, bin_width=1.0, label_mode="interval",
                       fill_color="#e0e0e0", stroke_width=1.2):
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
                                       fill=fill_color, stroke="black", stroke_width=stroke_width))

            if label_mode == "center":
                label = self._format_number(center_val, self.cfg.tick_rounding[0])
                y_num = py_bottom + 20 + self.cfg.offset_xaxis_num_y
                self.render_text_tex_lite(px_center, y_num, label, anchor="middle")

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
            self.dwg.add(
                self.dwg.rect(insert=(x_q1, y_top), size=(x_q3 - x_q1, box_height), fill="white", stroke="black",
                              stroke_width=1.5))
            self.dwg.add(self.dwg.line(start=(x_med, y_top), end=(x_med, y_bottom), stroke="black", stroke_width=1.5))
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
                    label_group.add(self.dwg.rect(insert=(x_label_pos - w / 2 - 2, y_label_pos - box.ascent - 2),
                                                  size=(w + 4, h + 4), fill="white",
                                                  fill_opacity=str(self.cfg.label_background_opacity)))
                self.render_text_tex_lite(x_label_pos, y_label_pos, stats.label, anchor="middle", italic=False,
                                          container=label_group)

    def draw_scatter(self, x_data: List[float], y_data: List[float],
                     connect=False,
                     line_of_best_fit=None,
                     marker_type="circle",
                     marker_size=3.5,
                     color="black",
                     lob_color="black",
                     lob_width=1.5,
                     lob_style="solid"):

        points = []
        for x, y in zip(x_data, y_data):
            px, py = self.math_to_screen(x, y)
            points.append((px, py))

            if marker_type == "circle":
                self.dwg.add(self.dwg.circle(center=(px, py), r=marker_size, fill=color, stroke="none"))
            elif marker_type == "hollow_circle":
                self.dwg.add(
                    self.dwg.circle(center=(px, py), r=marker_size, fill="white", stroke=color, stroke_width=1.5))
            elif marker_type == "square":
                s = marker_size * 2
                self.dwg.add(
                    self.dwg.rect(insert=(px - marker_size, py - marker_size), size=(s, s), fill=color, stroke="none"))
            elif marker_type == "cross":
                s = marker_size
                self.dwg.add(
                    self.dwg.line(start=(px - s, py - s), end=(px + s, py + s), stroke=color, stroke_width=1.5))
                self.dwg.add(
                    self.dwg.line(start=(px - s, py + s), end=(px + s, py - s), stroke=color, stroke_width=1.5))
            elif marker_type == "plus":
                s = marker_size
                self.dwg.add(self.dwg.line(start=(px - s, py), end=(px + s, py), stroke=color, stroke_width=1.5))
                self.dwg.add(self.dwg.line(start=(px, py - s), end=(px, py + s), stroke=color, stroke_width=1.5))

        if connect and len(points) > 1:
            path_d = ["M", f"{points[0][0]},{points[0][1]}"]
            for p in points[1:]: path_d.append(f"L {p[0]},{p[1]}")
            self.dwg.add(self.dwg.path(d=" ".join(path_d), stroke=color, fill="none", stroke_width=1.5))

        if line_of_best_fit:
            m, c = line_of_best_fit

            # --- BOX CLIPPING LOGIC ---
            x_min_grid = -1 * self.cfg.grid_scale[0] * self.idx_yaxis
            x_max_grid = self.cfg.grid_scale[0] * (self.num_major_x - self.idx_yaxis)
            y_min_grid = -1 * self.cfg.grid_scale[1] * (self.num_major_y - self.idx_xaxis)
            y_max_grid = self.cfg.grid_scale[1] * self.idx_xaxis

            candidates = []

            # 1. Intersect with x = x_min
            y_at_xmin = m * x_min_grid + c
            if y_min_grid <= y_at_xmin <= y_max_grid:
                candidates.append((x_min_grid, y_at_xmin))

            # 2. Intersect with x = x_max
            y_at_xmax = m * x_max_grid + c
            if y_min_grid <= y_at_xmax <= y_max_grid:
                candidates.append((x_max_grid, y_at_xmax))

            # 3. Intersect with y = y_min
            if abs(m) > 1e-9:
                x_at_ymin = (y_min_grid - c) / m
                if x_min_grid <= x_at_ymin <= x_max_grid:
                    candidates.append((x_at_ymin, y_min_grid))

            # 4. Intersect with y = y_max
            if abs(m) > 1e-9:
                x_at_ymax = (y_max_grid - c) / m
                if x_min_grid <= x_at_ymax <= x_max_grid:
                    candidates.append((x_at_ymax, y_max_grid))

            unique_pts = list(set(candidates))
            unique_pts.sort(key=lambda p: p[0])

            if len(unique_pts) >= 2:
                p1 = unique_pts[0]
                p2 = unique_pts[-1]

                px1, py1 = self.math_to_screen(p1[0], p1[1])
                px2, py2 = self.math_to_screen(p2[0], p2[1])

                # --- FIX: Only pass stroke_dasharray if needed ---
                line_kwargs = {
                    "stroke": lob_color,
                    "stroke_width": lob_width
                }
                if lob_style == "dotted":
                    line_kwargs["stroke_dasharray"] = "4,4"

                self.dwg.add(self.dwg.line(start=(px1, py1), end=(px2, py2), **line_kwargs))