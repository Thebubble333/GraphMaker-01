import re
import math
from typing import List, Any
from .graph_base import BaseGraphEngine
from .stats_analyser import StatsAnalyser 

class StatsGraphEngine(BaseGraphEngine):

    # ==========================================
    # 1. HISTOGRAMS
    # ==========================================
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

    # ==========================================
    # 2. BOX PLOTS
    # ==========================================
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

            # Whiskers
            self.dwg.add(self.dwg.line(start=(x_min, y_center), end=(x_q1, y_center), stroke="black", stroke_width=1.5))
            self.dwg.add(self.dwg.line(start=(x_q3, y_center), end=(x_max, y_center), stroke="black", stroke_width=1.5))

            # Caps
            if self.cfg.show_whisker_caps:
                self.dwg.add(self.dwg.line(start=(x_min, y_top + 5), end=(x_min, y_bottom - 5), stroke="black", stroke_width=1.5))
                self.dwg.add(self.dwg.line(start=(x_max, y_top + 5), end=(x_max, y_bottom - 5), stroke="black", stroke_width=1.5))

            # Box
            self.dwg.add(self.dwg.rect(insert=(x_q1, y_top), size=(x_q3 - x_q1, box_height),
                                       fill="white", stroke="black", stroke_width=1.5))
            # Median
            self.dwg.add(self.dwg.line(start=(x_med, y_top), end=(x_med, y_bottom), stroke="black", stroke_width=1.5))

            # Outliers
            for out in stats.outliers:
                xo, _ = self.math_to_screen(out, 0)
                self.dwg.add(self.dwg.circle(center=(xo, y_center), r=3, fill="white", stroke="black", stroke_width=1.5))

            # Labels
            if stats.label:
                x_label_pos = (x_q1 + x_q3) / 2
                y_label_pos = y_top - 2 + self.cfg.offset_box_label_y
                
                # We create a draggable group for the label
                safe_label = re.sub(r'[^a-zA-Z0-9]', '', stats.label)
                unique_id = f"lbl_box_{safe_label}_{i}"
                label_group = self.dwg.g(class_="draggable-label", id_=unique_id)
                self.dwg.add(label_group)

                if self.cfg.show_label_background:
                    # Approximation of background size
                    # Note: TexEngine is usually available on self.tex_engine in BaseGraphEngine
                    try:
                        box = self.tex_engine.parse_layout(stats.label, font_size=11)
                        w, h = box.width, box.height
                        label_group.add(self.dwg.rect(insert=(x_label_pos - w / 2 - 2, y_label_pos - box.ascent - 2),
                                                      size=(w + 4, h + 4), fill="white",
                                                      fill_opacity=str(self.cfg.label_background_opacity)))
                    except:
                        pass

                self.render_text_tex_lite(x_label_pos, y_label_pos, stats.label, anchor="middle", italic=False, container=label_group)

    # ==========================================
    # 3. SCATTER PLOTS
    # ==========================================
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
                self.dwg.add(self.dwg.circle(center=(px, py), r=marker_size, fill="white", stroke=color, stroke_width=1.5))
            elif marker_type == "square":
                s = marker_size * 2
                self.dwg.add(self.dwg.rect(insert=(px - marker_size, py - marker_size), size=(s, s), fill=color, stroke="none"))
            elif marker_type == "cross":
                s = marker_size
                self.dwg.add(self.dwg.line(start=(px - s, py - s), end=(px + s, py + s), stroke=color, stroke_width=1.5))
                self.dwg.add(self.dwg.line(start=(px - s, py + s), end=(px + s, py - s), stroke=color, stroke_width=1.5))
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
            
            # Calculate intersection with graph bounds
            x_min_grid = -1 * self.cfg.grid_scale[0] * self.idx_yaxis
            x_max_grid = self.cfg.grid_scale[0] * (self.num_major_x - self.idx_yaxis)
            y_min_grid = -1 * self.cfg.grid_scale[1] * (self.num_major_y - self.idx_xaxis)
            y_max_grid = self.cfg.grid_scale[1] * self.idx_xaxis

            candidates = []
            
            # x = x_min
            y_at_xmin = m * x_min_grid + c
            if y_min_grid <= y_at_xmin <= y_max_grid: candidates.append((x_min_grid, y_at_xmin))
            
            # x = x_max
            y_at_xmax = m * x_max_grid + c
            if y_min_grid <= y_at_xmax <= y_max_grid: candidates.append((x_max_grid, y_at_xmax))
            
            if abs(m) > 1e-9:
                # y = y_min
                x_at_ymin = (y_min_grid - c) / m
                if x_min_grid <= x_at_ymin <= x_max_grid: candidates.append((x_at_ymin, y_min_grid))
                
                # y = y_max
                x_at_ymax = (y_max_grid - c) / m
                if x_min_grid <= x_at_ymax <= x_max_grid: candidates.append((x_at_ymax, y_max_grid))

            unique_pts = list(set(candidates))
            unique_pts.sort(key=lambda p: p[0])

            if len(unique_pts) >= 2:
                p1 = unique_pts[0]
                p2 = unique_pts[-1]
                px1, py1 = self.math_to_screen(p1[0], p1[1])
                px2, py2 = self.math_to_screen(p2[0], p2[1])

                line_kwargs = {"stroke": lob_color, "stroke_width": lob_width}
                if lob_style == "dotted":
                    line_kwargs["stroke_dasharray"] = "4,4"

                self.dwg.add(self.dwg.line(start=(px1, py1), end=(px2, py2), **line_kwargs))

    # ==========================================
    # 4. VISUAL QUARTILES
    # ==========================================
    def draw_visual_quartiles(self, vq_data, radius=20, spread=1.0, font_size=14, show_legend=True,
                              arrow_len=40, q_arrow_offset=10, legend_y_offset=0,
                              highlight_offset=4, highlight_width=3,
                              color_q1="blue", color_med="red", color_q3="blue"):
        n = len(vq_data.sorted_data)
        
        total_w = self.width_pixels
        total_h = self.height_pixels
        
        available_w = total_w - 100 
        item_spacing = (available_w / n) * spread
        
        group_width = (n - 1) * item_spacing
        start_x = (total_w - group_width) / 2
        base_y = total_h / 2 - 20 

        c_fill = "#f0f0f0"
        
        def draw_indicator(node, label, color, position="bottom", extra_y_offset=0):
            cx = start_x + node.index * item_spacing
            
            if node.type == "exact":
                self.dwg.add(self.dwg.circle(center=(cx, base_y), r=radius + highlight_offset,
                                             fill="none", stroke=color, stroke_width=highlight_width))
            else:
                bar_h = radius * 2.5
                self.dwg.add(self.dwg.line(start=(cx, base_y - bar_h/2), 
                                           end=(cx, base_y + bar_h/2),
                                           stroke=color, stroke_width=highlight_width))

            ah_len = 12
            text_pad = 5
            current_arrow_len = arrow_len + extra_y_offset

            if position == "bottom":
                y_tip = base_y + radius + 10 + extra_y_offset
                y_base = y_tip + current_arrow_len
                y_line_end = y_tip + ah_len 
                
                self.dwg.add(self.dwg.line(start=(cx, y_base), end=(cx, y_line_end), stroke=color, stroke_width=2))
                self._draw_arrowhead(cx, y_tip, direction="up", color=color)
                self.render_text_tex_lite(cx, y_base + text_pad + 10, f"{label}", 
                                          anchor="middle", color=color, font_size=font_size+2)
            else:
                y_tip = base_y - radius - 10
                y_base = y_tip - current_arrow_len
                y_line_end = y_tip - ah_len

                self.dwg.add(self.dwg.line(start=(cx, y_base), end=(cx, y_line_end), stroke=color, stroke_width=2))
                self._draw_arrowhead(cx, y_tip, direction="down", color=color)
                self.render_text_tex_lite(cx, y_base - 5, f"{label}", 
                                          anchor="middle", color=color, font_size=font_size+2)

        for i, val in enumerate(vq_data.sorted_data):
            cx = start_x + i * item_spacing
            self.dwg.add(self.dwg.circle(center=(cx, base_y), r=radius, 
                                         fill=c_fill, stroke="black", stroke_width=2))
            
            val_str = f"{int(val)}" if val.is_integer() else f"{val}"
            self.render_text_tex_lite(cx, base_y + font_size/3, val_str, anchor="middle", font_size=font_size)

        draw_indicator(vq_data.q1, "Q1", color_q1, "bottom", extra_y_offset=q_arrow_offset)
        draw_indicator(vq_data.median, "Median", color_med, "top")
        draw_indicator(vq_data.q3, "Q3", color_q3, "bottom", extra_y_offset=q_arrow_offset)

        if show_legend:
            leg_x = 50
            leg_y = total_h - 40 + legend_y_offset 
            leg_c_exact = "red"
            leg_c_split = "blue"
            
            self.dwg.add(self.dwg.circle(center=(leg_x, leg_y), r=10, fill="none", stroke=leg_c_exact, stroke_width=highlight_width))
            self.render_text_tex_lite(leg_x + 20, leg_y + 4, "Value used directly", font_size=12)
            
            self.dwg.add(self.dwg.line(start=(leg_x + 200, leg_y - 10), end=(leg_x + 200, leg_y + 10), stroke=leg_c_split, stroke_width=highlight_width))
            self.render_text_tex_lite(leg_x + 215, leg_y + 4, "Average taken", font_size=12)

    # ==========================================
    # 5. STEM AND LEAF
    # ==========================================
    def draw_stem_and_leaf(self, left_data: List[float], right_data: List[float], 
                           title_left="Left Group", title_right="Right Group", 
                           stem_value=10, key_label="Key: 4|2 = 42",
                           font_size=14, row_height=25, col_width=20,
                           split_stems=False, show_quartiles=False, debug_mode=False):
        
        analyser = StatsAnalyser() 
        is_back_to_back = len(left_data) > 0 and len(right_data) > 0
        
        if not is_back_to_back and len(left_data) > 0:
            right_dict, min_s, max_s = analyser.get_stem_leaf_data(left_data, stem_value, split_stems)
            left_dict = {}
            title_right = title_left 
            title_left = ""
            active_data_right = left_data
            active_data_left = []
        else:
            right_dict, min_r, max_r = analyser.get_stem_leaf_data(right_data, stem_value, split_stems) if right_data else ({}, 0, 0)
            left_dict, min_l, max_l = analyser.get_stem_leaf_data(left_data, stem_value, split_stems) if left_data else ({}, 0, 0)
            active_data_right = right_data
            active_data_left = left_data
            
            if not right_data:
                min_s, max_s = min_l, max_l
            elif not left_data:
                min_s, max_s = min_r, max_r
            else:
                min_s = min(min_l, min_r)
                max_s = max(max_l, max_r)

        def get_stem_keys(min_k, max_k, is_split):
            keys = []
            curr = min_k
            step = 0.5 if is_split else 1.0
            while curr <= max_k + 0.001:
                if is_split:
                    keys.append(round(curr, 1))
                else:
                    keys.append(int(round(curr)))
                curr += step
            return sorted(list(set(keys)))

        all_stems = get_stem_keys(min_s, max_s, split_stems)

        center_x = self.width_pixels / 2
        
        # --- TIGHTER LAYOUT ---
        start_y = self.margin_top + 60 
        
        title_y = start_y - 25
        if is_back_to_back:
            self.render_text_tex_lite(center_x - 40, title_y, title_left, anchor="end", font_size=font_size+2, color="black")
            self.render_text_tex_lite(center_x + 40, title_y, title_right, anchor="start", font_size=font_size+2, color="black")
        else:
            self.render_text_tex_lite(center_x, title_y, title_right, anchor="middle", font_size=font_size+2, color="black")

        # Key (Draggable)
        key_id = "lbl_stem_key"
        key_grp = self.dwg.g(class_="draggable-label", id_=key_id)
        self.dwg.add(key_grp)
        try:
            kb = self.tex_engine.parse_layout(key_label, font_size=font_size, italic=True)
            kw, kh = kb.width, kb.height
            key_grp.add(self.dwg.rect(insert=(self.margin_left - 5, self.margin_top - kh - 5), 
                                      size=(kw + 10, kh + 10), 
                                      fill="white", fill_opacity="0.9"))
        except:
            pass 
        self.render_text_tex_lite(self.margin_left, self.margin_top, key_label, 
                                  anchor="start", font_size=font_size, italic=True,
                                  container=key_grp)

        line_height = (len(all_stems) * row_height) + 30
        stem_col_half_width = font_size * 0.8
        
        line_start_y = start_y - 10
        line_end_y = start_y + line_height - 30 
        
        self.dwg.add(self.dwg.line(start=(center_x - stem_col_half_width, line_start_y), 
                                   end=(center_x - stem_col_half_width, line_end_y), 
                                   stroke="black", stroke_width=1.5))
        self.dwg.add(self.dwg.line(start=(center_x + stem_col_half_width, line_start_y), 
                                   end=(center_x + stem_col_half_width, line_end_y), 
                                   stroke="black", stroke_width=1.5))

        current_y = start_y + row_height/2 
        position_map = {'left': {}, 'right': {}}
        stem_y_map = {} 

        for stem_key in all_stems:
            stem_display = str(int(stem_key))
            self.render_text_tex_lite(center_x, current_y, stem_display, anchor="middle", font_size=font_size, color="black")
            
            position_map['left'][stem_key] = []
            position_map['right'][stem_key] = []
            stem_y_map[stem_key] = current_y

            if stem_key in left_dict:
                leaves = sorted(left_dict[stem_key])
                for i, leaf in enumerate(leaves):
                    pos_x = (center_x - stem_col_half_width - 15) - (i * col_width)
                    self.render_text_tex_lite(pos_x, current_y, str(leaf), anchor="middle", font_size=font_size, color="black")
                    position_map['left'][stem_key].append((pos_x, current_y))

            if stem_key in right_dict:
                leaves = sorted(right_dict[stem_key])
                for i, leaf in enumerate(leaves):
                    pos_x = (center_x + stem_col_half_width + 15) + (i * col_width)
                    self.render_text_tex_lite(pos_x, current_y, str(leaf), anchor="middle", font_size=font_size, color="black")
                    position_map['right'][stem_key].append((pos_x, current_y))

            current_y += row_height

        if show_quartiles:
            
            def draw_stat_highlights(data_set, side):
                if not data_set: return
                vq = analyser.get_visual_quartiles(data_set)
                
                all_coords = []
                for s_key in sorted(position_map[side].keys()):
                    all_coords.extend(position_map[side][s_key])
                
                if debug_mode:
                    for i in range(len(all_coords)-1):
                        p1 = all_coords[i]
                        p2 = all_coords[i+1]
                        self.dwg.add(self.dwg.line(start=(p1[0], p1[1]+5), end=(p2[0], p2[1]+5), 
                                                   stroke="red", stroke_width=0.5, stroke_opacity=0.5))

                def highlight_node(node):
                    color = "red" if node.type == "exact" else "blue"
                    
                    if node.type == "exact":
                        idx = int(node.index)
                        if 0 <= idx < len(all_coords):
                            cx, cy = all_coords[idx]
                            self.dwg.add(self.dwg.circle(center=(cx, cy - 4), r=font_size*0.85, 
                                                         fill="none", stroke=color, stroke_width=2.5))
                    else:
                        idx_low = int(math.floor(node.index))
                        idx_high = int(math.ceil(node.index))
                        
                        if idx_high < len(all_coords):
                            c1 = all_coords[idx_low]
                            c2 = all_coords[idx_high]
                            
                            bar_h = font_size * 1.5
                            
                            # Same Row Check
                            if abs(c1[1] - c2[1]) < 1.0:
                                mx = (c1[0] + c2[0]) / 2
                                my = c1[1]
                                self.dwg.add(self.dwg.line(start=(mx, my - bar_h/2 - 4), 
                                                           end=(mx, my + bar_h/2 - 4), 
                                                           stroke=color, stroke_width=3))
                            else:
                                # DIFFERENT ROW - SMART PLACEMENT
                                target_key, _ = analyser.get_stem_leaf_position(node.value, stem_value, split_stems)
                                target_y = stem_y_map.get(target_key)
                                if target_y is None: target_y = c2[1]
                                
                                offset = col_width / 2 + 2 
                                
                                is_row_1 = abs(target_y - c1[1]) < 1.0
                                is_row_2 = abs(target_y - c2[1]) < 1.0
                                
                                if is_row_1:
                                    draw_x = c1[0] - offset if side == 'left' else c1[0] + offset
                                    draw_y = c1[1]
                                    self.dwg.add(self.dwg.line(start=(draw_x, draw_y - bar_h/2 - 4),
                                                               end=(draw_x, draw_y + bar_h/2 - 4),
                                                               stroke=color, stroke_width=3))
                                    
                                elif is_row_2:
                                    draw_x = c2[0] + offset if side == 'left' else c2[0] - offset
                                    draw_y = c2[1]
                                    self.dwg.add(self.dwg.line(start=(draw_x, draw_y - bar_h/2 - 4),
                                                               end=(draw_x, draw_y + bar_h/2 - 4),
                                                               stroke=color, stroke_width=3))

                highlight_node(vq.q1)
                highlight_node(vq.median)
                highlight_node(vq.q3)

            if active_data_right:
                draw_stat_highlights(active_data_right, 'right')
            if active_data_left:
                draw_stat_highlights(active_data_left, 'left')

    def _draw_arrowhead(self, x, y, direction="right", color="black"):
        length = 12
        width = 12
        half_w = width / 2
        if direction == "right":
            points = [(x + length, y), (x, y - half_w), (x, y + half_w)]
        elif direction == "up":
            points = [(x, y), (x - half_w, y + length), (x + half_w, y + length)]
        elif direction == "down":
            points = [(x, y), (x - half_w, y - length), (x + half_w, y - length)]
        else:
            return
        self.dwg.add(self.dwg.polygon(points=points, fill=color))

    def get_svg_string(self):
        return self.dwg.tostring()