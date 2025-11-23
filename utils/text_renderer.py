import svgwrite
import re
from dataclasses import dataclass, field
from typing import List, Optional, Union, Tuple, Dict

# --- IMPORT METRICS ---
# Ensure font_metrics.py exists in the same directory
try:
    from .font_metrics import (
        CHAR_WIDTHS_ITALIC,
        CHAR_WIDTHS_NORMAL,
        KERNING_ITALIC,
        KERNING_NORMAL
    )
except ImportError:
    try:
        from font_metrics import (
            CHAR_WIDTHS_ITALIC,
            CHAR_WIDTHS_NORMAL,
            KERNING_ITALIC,
            KERNING_NORMAL
        )
    except ImportError:
        print("Error: 'font_metrics.py' not found.")
        # Fallback empty dicts
        CHAR_WIDTHS_ITALIC = {}
        CHAR_WIDTHS_NORMAL = {}
        KERNING_ITALIC = {}
        KERNING_NORMAL = {}

# Constants
LINE_THICKNESS_FACTOR = 0.04
LEFT_OVERFLOW_MAP = {'y': 0.2, 'j': 0.15, 'J': 0.1, 'f': 0.1}


def get_char_width(char: str, font_size: float, is_math: bool = False) -> float:
    if is_math:
        val = CHAR_WIDTHS_ITALIC.get(char, 0.5)
    else:
        val = CHAR_WIDTHS_NORMAL.get(char, 0.5)
    try:
        return float(val) * font_size
    except:
        return 0.5 * font_size


def get_kerning(left_char: str, right_char: str, font_size: float, is_math: bool = False) -> float:
    """Look up kerning value between two characters."""
    pair = (left_char, right_char)
    val = 0.0
    if is_math:
        val = KERNING_ITALIC.get(pair, 0.0)
    else:
        val = KERNING_NORMAL.get(pair, 0.0)
    return val * font_size


@dataclass
class Box:
    width: float
    ascent: float
    descent: float
    left_overflow: float = 0.0  # Restored attribute

    @property
    def height(self): return self.ascent + self.descent

    def render(self, dwg, x, y, color="black", container=None): pass


@dataclass
class SpaceBox(Box):
    def render(self, dwg, x, y, color="black", container=None): pass


@dataclass
class CharBox(Box):
    char: str = ""
    font_size: float = 16.0
    is_math: bool = False

    def render(self, dwg, x, y, color="black", container=None):
        target = container if container else dwg
        style = "italic" if self.is_math else "normal"
        target.add(dwg.text(self.char, insert=(x, y), font_size=self.font_size,
                            font_family="Times New Roman", fill=color, font_style=style))


@dataclass
class RowBox(Box):
    children: List[Box] = field(default_factory=list)

    def render(self, dwg, x, y, color="black", container=None):
        curr_x = x
        prev_child = None

        for child in self.children:
            # --- KERNING LOGIC ---
            if prev_child and isinstance(prev_child, CharBox) and isinstance(child, CharBox):
                if prev_child.is_math == child.is_math:
                    kern_val = get_kerning(prev_child.char, child.char, child.font_size, child.is_math)
                    curr_x += kern_val

            child.render(dwg, curr_x, y, color, container)
            curr_x += child.width
            prev_child = child


@dataclass
class FracBox(Box):
    numerator: Box = field(default_factory=lambda: Box(0, 0, 0))
    denominator: Box = field(default_factory=lambda: Box(0, 0, 0))
    line_thick: float = 1.0
    axis_height: float = 4.0

    def render(self, dwg, x, y, color="black", container=None):
        target = container if container else dwg
        mid_x = x + self.width / 2
        line_y = y - self.axis_height
        target.add(dwg.line((x, line_y), (x + self.width, line_y), stroke=color, stroke_width=self.line_thick))
        padding = self.line_thick * 2.0
        num_baseline = line_y - padding - self.numerator.descent
        self.numerator.render(dwg, mid_x - self.numerator.width / 2, num_baseline, color, container)
        den_baseline = line_y + padding + self.denominator.ascent
        self.denominator.render(dwg, mid_x - self.denominator.width / 2, den_baseline, color, container)


@dataclass
class SqrtBox(Box):
    content: Box = field(default_factory=lambda: Box(0, 0, 0))
    tick_width: float = 10.0
    line_thick: float = 1.0

    def render(self, dwg, x, y, color="black", container=None):
        target = container if container else dwg
        w = self.content.width
        pad_top = self.line_thick * 3
        pad_right = self.line_thick * 2
        line_y = y - self.content.ascent - pad_top
        path = dwg.path(stroke=color, stroke_width=self.line_thick, fill="none", stroke_linecap="square",
                        stroke_linejoin="miter")
        start_x = x
        path.push('M', start_x, y - (self.content.ascent * 0.6))
        path.push('L', start_x + (self.tick_width * 0.4), y)
        path.push('L', start_x + self.tick_width, line_y)
        path.push('L', start_x + self.tick_width + w + pad_right, line_y)
        target.add(path)
        self.content.render(dwg, x + self.tick_width + (pad_right / 2), y, color, container)


@dataclass
class SupBox(Box):
    base: Box = field(default_factory=lambda: Box(0, 0, 0))
    sup: Box = field(default_factory=lambda: Box(0, 0, 0))

    def render(self, dwg, x, y, color="black", container=None):
        self.base.render(dwg, x, y, color, container)
        sup_x = x + self.base.width + (self.base.width * 0.02)
        self.sup.render(dwg, sup_x, y - (self.base.ascent * 0.4), color, container)


class TexEngine:
    def __init__(self):
        pass

    def measure(self, text, font_size=16):
        box = self.parse_layout(text, font_size)
        return box.width, box.height

    def parse_layout(self, text, font_size=16):
        tokens = self._tokenize(text)
        nodes, _ = self._parse_group(tokens)
        return self._layout(nodes, font_size)

    def _tokenize(self, text):
        token_re = re.compile(
            r'(\\[a-zA-Z]+)|(sin|cos|tan|csc|sec|cot|ln|log|exp)|([{}^_])|([a-zA-Z0-9\+\-\=\.\,\(\)\s\|])')
        tokens = []
        for match in token_re.finditer(text):
            s = match.group(0)
            if s: tokens.append(s)
        return tokens

    def _parse_group(self, tokens, inside_brace=False):
        nodes = []
        while tokens:
            tok = tokens.pop(0)
            if tok.isspace():
                nodes.append({'type': 'space'});
                continue
            if tok == '}':
                if inside_brace: return nodes, True
                continue
            elif tok == '{':
                group, _ = self._parse_group(tokens, True)
                nodes.append({'type': 'group', 'content': group})
            elif tok in [r'\left', r'\right']:
                continue
            elif tok in ['sin', 'cos', 'tan', 'csc', 'sec', 'cot', 'ln', 'log', 'exp']:
                nodes.append({'type': 'func', 'val': tok})
            elif tok == '^':
                if not nodes: continue
                if not tokens: break
                next_tok = tokens[0]
                if next_tok == '{':
                    tokens.pop(0)
                    sup_content, _ = self._parse_group(tokens, True)
                    sup_node = {'type': 'group', 'content': sup_content}
                elif next_tok.startswith('\\'):
                    tokens.pop(0)
                    sup_node = self._parse_next_atom([next_tok] + tokens)
                else:
                    tokens.pop(0)
                    sup_node = {'type': 'char', 'val': next_tok}
                base = nodes.pop()
                nodes.append({'type': 'sup', 'base': base, 'sup': sup_node})
            elif tok.startswith('\\'):
                cmd = tok[1:]
                if cmd == 'frac':
                    num = self._parse_next_atom(tokens)
                    den = self._parse_next_atom(tokens)
                    nodes.append({'type': 'frac', 'num': num, 'den': den})
                elif cmd == 'sqrt':
                    content = self._parse_next_atom(tokens)
                    nodes.append({'type': 'sqrt', 'content': content})
                elif cmd in ['sin', 'cos', 'tan', 'ln', 'log', 'exp']:
                    nodes.append({'type': 'func', 'val': cmd})
                elif cmd in ['pi', 'theta', 'alpha', 'beta', 'gamma', 'Delta']:
                    greek = {'pi': 'π', 'theta': 'θ', 'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'Delta': 'Δ'}[cmd]
                    nodes.append({'type': 'char', 'val': greek})
                else:
                    nodes.append({'type': 'text', 'val': cmd})
            else:
                nodes.append({'type': 'char', 'val': tok})
        return nodes, False

    def _parse_next_atom(self, tokens):
        if not tokens: return {'type': 'char', 'val': '?'}
        tok = tokens.pop(0)
        if tok == '{':
            group, _ = self._parse_group(tokens, True)
            return {'type': 'group', 'content': group}
        if tok.startswith('\\'):
            cmd = tok[1:]
            if cmd in ['pi', 'theta', 'alpha', 'beta']:
                greek = {'pi': 'π', 'theta': 'θ'}.get(cmd, '?')
                return {'type': 'char', 'val': greek}
            return {'type': 'text', 'val': cmd}
        return {'type': 'char', 'val': tok}

    def _layout(self, nodes, font_size) -> Box:
        boxes = []

        def resolve(n, size):
            if isinstance(n, list): return self._layout(n, size)
            if n['type'] == 'group': return self._layout(n['content'], size)
            return self._layout([n], size)

        def get_vert_metrics(char, fsize):
            if char in "()[]{}|/\\bdfhklt1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                return fsize * 0.8, fsize * 0.25
            elif char in "gpqy":
                return fsize * 0.55, fsize * 0.35
            elif char in "acemnorsuvwxz":
                return fsize * 0.55, 0.0
            else:
                return fsize * 0.8, fsize * 0.25

        for node in nodes:
            t = node['type']
            if t == 'space':
                boxes.append(SpaceBox(width=font_size * 0.2, ascent=0, descent=0))
            elif t == 'char':
                txt = node['val']
                if txt in ['=', '+', '-']:
                    boxes.append(SpaceBox(width=font_size * 0.15, ascent=0, descent=0))
                    display_char = txt.replace('-', '\u2212')
                    w = get_char_width(display_char, font_size, is_math=False)
                    boxes.append(CharBox(width=w, ascent=font_size * 0.8, descent=font_size * 0.2, char=display_char,
                                         font_size=font_size, is_math=False))
                    boxes.append(SpaceBox(width=font_size * 0.15, ascent=0, descent=0))
                else:
                    is_math = txt.isalpha()
                    w = get_char_width(txt, font_size, is_math=is_math)
                    asc, desc = get_vert_metrics(txt, font_size)

                    # CALCULATE LEFT OVERFLOW
                    l_off = 0.0
                    if is_math and txt in LEFT_OVERFLOW_MAP:
                        l_off = font_size * LEFT_OVERFLOW_MAP[txt]

                    boxes.append(
                        CharBox(width=w, ascent=asc, descent=desc, left_overflow=l_off, char=txt, font_size=font_size,
                                is_math=is_math))

            elif t == 'text' or t == 'func':
                txt = node['val']
                for char in txt:
                    w = get_char_width(char, font_size, is_math=False)
                    asc, desc = get_vert_metrics(char, font_size)
                    boxes.append(
                        CharBox(width=w, ascent=asc, descent=desc, char=char, font_size=font_size, is_math=False))
            elif t == 'group':
                boxes.append(self._layout(node['content'], font_size))
            elif t == 'frac':
                num_node = node['num'];
                den_node = node['den']

                def to_list(n):
                    return n['content'] if n['type'] == 'group' else [n]

                num_box = self._layout(to_list(num_node), font_size * 0.8)
                den_box = self._layout(to_list(den_node), font_size * 0.8)
                w = max(num_box.width, den_box.width) + 6
                axis_h = font_size * 0.28
                thick = font_size * LINE_THICKNESS_FACTOR
                padding = thick * 2.0
                new_asc = axis_h + padding + num_box.descent + num_box.ascent
                new_desc = den_box.ascent + den_box.descent + padding - axis_h
                boxes.append(FracBox(width=w, ascent=new_asc, descent=new_desc, numerator=num_box, denominator=den_box,
                                     line_thick=thick, axis_height=axis_h))
            elif t == 'sqrt':
                content_node = node['content']

                def to_list(n):
                    return n['content'] if n['type'] == 'group' else [n]

                content = self._layout(to_list(content_node), font_size)
                tick_w = font_size * 0.5
                line_thick = font_size * LINE_THICKNESS_FACTOR
                pad_right = line_thick * 2
                total_w = content.width + tick_w + pad_right
                boxes.append(SqrtBox(width=total_w, ascent=content.ascent + 6, descent=content.descent, content=content,
                                     tick_width=tick_w, line_thick=line_thick))
            elif t == 'sup':
                base_box = resolve(node['base'], font_size)

                def to_list(n):
                    return n['content'] if n['type'] == 'group' else [n]

                sup_box = self._layout(to_list(node['sup']), font_size * 0.7)
                base_box.width += 0.0
                total_w = base_box.width + sup_box.width
                total_asc = max(base_box.ascent, sup_box.ascent + base_box.ascent * 0.5)
                boxes.append(
                    SupBox(width=total_w, ascent=total_asc, descent=base_box.descent, base=base_box, sup=sup_box))

        total_w = sum(float(b.width) for b in boxes)

        # Propagate left overflow from first element
        l_overflow = 0.0
        if boxes and boxes[0].left_overflow > 0:
            l_overflow = boxes[0].left_overflow

        if not boxes: return Box(0.0, 0.0, 0.0)
        max_asc = max(float(b.ascent) for b in boxes)
        max_desc = max(float(b.descent) for b in boxes)
        return RowBox(width=total_w, ascent=max_asc, descent=max_desc, left_overflow=l_overflow, children=boxes)