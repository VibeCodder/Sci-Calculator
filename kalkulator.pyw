

import tkinter as tk
from tkinter import ttk
import math
import re
from fractions import Fraction

# ─── KOLORY ───────────────────────────────────────────────────────────────────
BG        = "#000000"
DISP_BG   = "#1e1e1e"
ACCENT    = "#00bcd4"
BTN_DARK  = "#262626"
BTN_MED   = "#333333"
BTN_BLUE  = "#4a69bd"
BTN_RED   = "#b33921"
BTN_TEAL  = "#0a8481"
BTN_PURP  = "#6e35a8"
FG        = "#ffffff"
FG_DIM    = "#aaaaaa"

EPSILON      = 2.220446049250313e-16
PHI          = (1 + math.sqrt(5)) / 2
FRAC_MAX_DEN = 1000

# ─── EVAL ENV ─────────────────────────────────────────────────────────────────
def _make_env(deg):
    d = lambda f: (lambda x: f(math.radians(x)))
    u = lambda f: (lambda x: math.degrees(f(x)))
    if deg:
        sin  = d(math.sin);  cos  = d(math.cos);  tan  = d(math.tan)
        cot  = lambda x: 1/d(math.tan)(x)
        sinh = d(math.sinh); cosh = d(math.cosh); tanh = d(math.tanh)
        coth = lambda x: 1/d(math.tanh)(x)
        asin = u(math.asin); acos = u(math.acos); atan = u(math.atan)
        acot = lambda x: math.degrees(math.atan(1/x))
    else:
        sin  = math.sin;  cos  = math.cos;  tan  = math.tan
        cot  = lambda x: 1/math.tan(x)
        sinh = math.sinh; cosh = math.cosh; tanh = math.tanh
        coth = lambda x: 1/math.tanh(x)
        asin = math.asin; acos = math.acos; atan = math.atan
        acot = lambda x: math.atan(1/x)
    return {
        "sin": sin, "cos": cos, "tan": tan, "cot": cot,
        "sinh": sinh, "cosh": cosh, "tanh": tanh, "coth": coth,
        "asin": asin, "acos": acos, "atan": atan, "acot": acot,
        "sqrt": math.sqrt,
        "cbrt": lambda x: math.copysign(abs(x)**(1/3), x),
        "log": math.log10, "lg": math.log10,
        "ln":  math.log,   "log2": math.log2,
        "abs": abs, "factorial": math.factorial, "exp": math.exp,
        "pi": math.pi, "e": math.e, "epsilon": EPSILON, "phi": PHI,
        "__builtins__": {},
    }

def _normalize(expr):
    expr = (expr
        .replace("×","*").replace("÷","/").replace("−","-")
        .replace("^","**")
        .replace("π","pi").replace("ε","epsilon").replace("φ","phi")
    )
    expr = re.sub(r'(\d)(pi|phi|epsilon)', r'\1*\2', expr)
    expr = re.sub(r'(\d)\(',              r'\1*(', expr)
    return expr

def _to_frac(val):
    try:
        f = Fraction(val).limit_denominator(FRAC_MAX_DEN)
        if f.denominator > 1 and abs(float(f)-val) < 1e-9:
            return f
    except Exception:
        pass
    return None

# ─── helpers: tokens → eval string ───────────────────────────────────────────
def tokens_to_eval_str(tokens):
    """Convert a token list (possibly nested) to evaluable string."""
    parts = []
    for t in tokens:
        if isinstance(t, str):
            s = (t.replace("π","pi").replace("ε","epsilon")
                  .replace("φ","phi").replace("÷","/")
                  .replace("×","*").replace("−","-"))
            parts.append(s)
        elif isinstance(t, FracToken):
            parts.append(t.eval_str())
        elif isinstance(t, ExprToken):
            parts.append(t.eval_str())
    return "".join(parts)

def tokens_to_display_str(tokens):
    """Convert a token list to human-readable string (for result label)."""
    parts = []
    for t in tokens:
        if isinstance(t, str):
            parts.append(t)
        elif isinstance(t, FracToken):
            n = tokens_to_display_str(t.num) or "0"
            d = tokens_to_display_str(t.den) or "1"
            parts.append("({}/{})".format(n, d))
        elif isinstance(t, ExprToken):
            defn = EXPR_DEFS[t.kind]
            label = defn[1]
            s0 = tokens_to_display_str(t.slots[0]) or "□"
            if t.two_slots:
                s1 = tokens_to_display_str(t.slots[1]) or "□"
                parts.append("{}({},{})".format(label, s0, s1))
            else:
                parts.append("{}({})".format(label, s0))
    return "".join(parts)

# ─── FRAC TOKEN ───────────────────────────────────────────────────────────────
class FracToken:
    """Fraction token. num and den are token-lists (support nesting)."""
    def __init__(self):
        self.num = []   # list of tokens
        self.den = []   # list of tokens
        self.editing  = False
        self.part     = "num"   # "num" or "den"
        self.cursor   = 0       # cursor in current slot token-list

    def eval_str(self):
        n = tokens_to_eval_str(self.num) or "0"
        d = tokens_to_eval_str(self.den) or "1"
        return "({}/{})".format(n, d)

    def active_slot(self):
        return self.num if self.part == "num" else self.den

    def copy_shallow(self):
        t = FracToken()
        t.num = list(self.num)
        t.den = list(self.den)
        t.editing = self.editing
        t.part = self.part
        t.cursor = self.cursor
        return t

# ─── EXPR TOKEN ───────────────────────────────────────────────────────────────
EXPR_DEFS = {
    "sqrt"    : ("sqrt({0})",               "√",           "prefix"),
    "cbrt"    : ("cbrt({0})",               "³√",          "prefix_root"),
    "log"     : ("log({0})",                "log",         "prefix"),
    "lg"      : ("lg({0})",                 "lg",          "prefix"),
    "ln"      : ("ln({0})",                 "ln",          "prefix"),
    "sin"     : ("sin({0})",                "sin",         "prefix"),
    "cos"     : ("cos({0})",                "cos",         "prefix"),
    "tan"     : ("tan({0})",                "tan",         "prefix"),
    "cot"     : ("cot({0})",                "cot",         "prefix"),
    "asin"    : ("asin({0})",               "asin",        "prefix"),
    "acos"    : ("acos({0})",               "acos",        "prefix"),
    "atan"    : ("atan({0})",               "atan",        "prefix"),
    "acot"    : ("acot({0})",               "acot",        "prefix"),
    "sinh"    : ("sinh({0})",               "sinh",        "prefix"),
    "cosh"    : ("cosh({0})",               "cosh",        "prefix"),
    "tanh"    : ("tanh({0})",               "tanh",        "prefix"),
    "coth"    : ("coth({0})",               "coth",        "prefix"),
    "factorial": ("factorial({0})",         "n",           "postfix_fact"),
    "exp"     : ("exp({0})",                "e",           "prefix_exp"),
    "abs"     : ("abs({0})",                "abs",         "abs"),
    "pow2"    : ("({0})**2",               "x",           "pow2"),
    "pown"    : ("({0})**(",               "x",           "pown"),
    "pow10"   : ("10**({0})",              "10",          "prefix_sup"),
    "xroot"   : ("xroot",                 "x",           "xroot"),
    "loga"    : ("loga",                  "log",         "prefix_sub"),
}

class ExprToken:
    """Expression token. slots are token-lists (support nesting)."""
    def __init__(self, kind):
        self.kind   = kind
        self.slots  = [[], []]   # each slot is a token-list
        self.editing  = False
        self.slot_idx = 0
        self.cursor   = 0        # cursor in active slot token-list

    @property
    def two_slots(self):
        return self.kind in ("pown", "xroot", "loga")

    def eval_str(self):
        defn = EXPR_DEFS[self.kind]
        tpl = defn[0]
        s0 = tokens_to_eval_str(self.slots[0]) or "0"
        s1 = tokens_to_eval_str(self.slots[1]) or "1"
        if self.kind == "pown":
            return "({})**({})" .format(s0, s1)
        if self.kind == "xroot":
            return "({})**(1/({}))".format(s1, s0)
        if self.kind == "loga":
            return "(log({}) / log({}))".format(s1, s0)
        return tpl.format(s0)

    def active_slot(self):
        return self.slots[self.slot_idx]

# ─── NESTED RENDERER ──────────────────────────────────────────────────────────
# We draw everything on a tk.Canvas using scaled coordinates.
# scale factor is stored in ExprDisplay and passed down.

class Renderer:
    """
    Draws a token list onto a canvas at given (x, cy) and returns new x.
    All font sizes and spacings are multiplied by `scale`.
    """
    BASE_EXPR  = 24
    BASE_FRAC  = 14
    BASE_SMALL = 12
    BASE_SUP   = 11
    SLOT_PAD   = 4
    CURSOR_W   = 2
    PAD_X      = 15
    PAD_Y      = 10

    def __init__(self, canvas, scale=1.0, blink_visible=True):
        self.cv    = canvas
        self.scale = scale
        self.blink_visible = blink_visible
        self._lbl_cache = {}
        # List of (tok, slot_spec, x0, y0, x1, y1) for mouse hit-testing.
        # slot_spec is "num"/"den" for FracToken, or int slot_idx for ExprToken.
        self.slot_hit_areas = []
        # Collected cursor line positions: list of (x, cy, half_h)
        self.cursor_positions = []

    def fs(self, base):
        """Scaled font size (min 6)."""
        return max(6, round(base * self.scale))

    def font_expr(self):  return ("Consolas", self.fs(self.BASE_EXPR),  "bold")
    def font_frac(self):  return ("Consolas", self.fs(self.BASE_FRAC),  "bold")
    def font_small(self): return ("Consolas", self.fs(self.BASE_SMALL), "bold")
    def font_sup(self):   return ("Consolas", self.fs(self.BASE_SUP),   "bold")

    def measure(self, text, font):
        key = (text, font)
        if key in self._lbl_cache:
            return self._lbl_cache[key]
        # padx=0, pady=0 — usuwamy domyślny padding Labela (1px z każdej strony),
        # żeby pomiar był spójny z create_text (które nie ma paddingu).
        lbl = tk.Label(self.cv, text=text, font=font, bg=DISP_BG, padx=0, pady=0)
        lbl.update_idletasks()
        w, h = lbl.winfo_reqwidth(), lbl.winfo_reqheight()
        lbl.destroy()
        self._lbl_cache[key] = (w, h)
        return w, h

    def sp(self, n):
        """Scale a pixel count."""
        return max(1, round(n * self.scale))

    def draw_cursor_line(self, x, cy, half_h=None):
        """Record cursor position for later drawing (does not draw immediately)."""
        if half_h is None:
            _, fh = self.measure("0", self.font_expr())
            half_h = fh // 2
        self.cursor_positions.append((x, cy, half_h))

    def draw_tokens(self, tokens, cursor_pos, cursor_active, x, cy,
                    editing_token=None):
        """
        Draw `tokens` starting at canvas-x=x, vertically centered at cy.
        cursor_pos: index in tokens where cursor sits (or None).
        cursor_active: whether to draw the cursor line.
        editing_token: FracToken/ExprToken currently being edited (may be nested).
        Returns new x after all tokens.
        """
        rects = []   # (x0, x1) for each token, used for click detection
        _, fh = self.measure("0", self.font_expr())
        half_h = fh // 2

        for i, tok in enumerate(tokens):
            if cursor_active and i == cursor_pos:
                self.draw_cursor_line(x, cy, half_h)

            x0 = x
            if isinstance(tok, FracToken):
                x = self._draw_frac(tok, x, cy, editing_token)
            elif isinstance(tok, ExprToken):
                x = self._draw_expr(tok, x, cy, editing_token)
            else:  # plain string
                tw, _ = self.measure(tok, self.font_expr())
                self.cv.create_text(x, cy, text=tok, font=self.font_expr(),
                                    fill=FG, anchor="w")
                x += tw
            rects.append((x0, x))

        if cursor_active and cursor_pos == len(tokens):
            self.draw_cursor_line(x, cy, half_h)

        return x, rects

    # ── Fraction ──────────────────────────────────────────────────────────────
    def _draw_frac(self, tok, x, cy, editing_token):
        PAD = self.sp(6)
        ff  = self.font_frac()

        # Build display strings for num/den (may be nested sub-renders)
        num_w, num_h, den_w, den_h = self._measure_slot_pair(tok, editing_token)

        # line_w = szerokość linii ułamkowej (max z licznika i mianownika + padding)
        # total_w = szerokość całego bloku ułamka (z marginesami bocznymi)
        # cx = środek bloku, względem którego centrujemy linię, licznik i mianownik
        line_w  = max(num_w, den_w) + PAD * 2
        SIDE_MARGIN = self.sp(4)
        total_w = line_w + SIDE_MARGIN * 2
        cx      = x + total_w // 2

        # The fraction bar sits exactly at cy (the math axis of the expression).
        # Numerator is centred above the bar; denominator below.
        BAR_GAP = self.sp(3)   # gap between slot content and the bar
        yl      = cy            # bar y-coordinate

        num_cy  = yl - BAR_GAP - num_h // 2
        den_cy  = yl + BAR_GAP + den_h // 2

        # is_editing helpers
        def _frac_contains_editor(ft, et):
            if et is None:
                return False
            if ft is et:
                return True
            for slot in (ft.num, ft.den):
                if self._tok_in_list(slot, et):
                    return True
            return False

        is_editing = tok.editing and _frac_contains_editor(tok, editing_token)
        num_active = tok.editing and tok == editing_token and tok.part == "num"
        den_active = tok.editing and tok == editing_token and tok.part == "den"

        # Determine whether editing_token lives inside num or den (deep nesting)
        num_has_editor = (editing_token is not None and editing_token is not tok
                          and self._tok_in_list(tok.num, editing_token))
        den_has_editor = (editing_token is not None and editing_token is not tok
                          and self._tok_in_list(tok.den, editing_token))

        # Licznik i mianownik zaczynamy od cx - ich_szerokosc/2
        # -> oba wyśrodkowane względem środka bloku (cx)
        num_x = cx - num_w // 2
        den_x = cx - den_w // 2

        # Highlight active slot background
        if num_active:
            self.cv.create_rectangle(
                num_x - 2, num_cy - num_h // 2 - 1,
                num_x + num_w + 2, num_cy + num_h // 2 + 1,
                fill="#003040", outline=ACCENT, width=1
            )

        # Record hit area for numerator slot (for mouse click detection)
        self.slot_hit_areas.append((tok, "num",
                                    num_x - 2, num_cy - num_h // 2 - 1,
                                    num_x + num_w + 2, num_cy + num_h // 2 + 1))

        num_cursor    = tok.cursor if num_active else None
        num_active_et = tok if num_active else (editing_token if num_has_editor else None)
        self._draw_slot_tokens(tok.num, num_active_et, num_cursor,
                               num_x, num_cy, ff)

        # Linia ułamkowa wyśrodkowana względem cx
        bar_color = ACCENT if is_editing else FG
        self.cv.create_line(cx - line_w // 2, yl, cx + line_w // 2, yl,
                            fill=bar_color, width=2)

        # Mianownik
        if den_active:
            self.cv.create_rectangle(
                den_x - 2, den_cy - den_h // 2 - 1,
                den_x + den_w + 2, den_cy + den_h // 2 + 1,
                fill="#003040", outline=ACCENT, width=1
            )

        # Record hit area for denominator slot
        self.slot_hit_areas.append((tok, "den",
                                    den_x - 2, den_cy - den_h // 2 - 1,
                                    den_x + den_w + 2, den_cy + den_h // 2 + 1))
        den_cursor    = tok.cursor if den_active else None
        den_active_et = tok if den_active else (editing_token if den_has_editor else None)
        self._draw_slot_tokens(tok.den, den_active_et, den_cursor,
                               den_x, den_cy, ff)

        return x + total_w

    def _measure_slot_pair(self, tok, editing_token):
        """Measure pixel sizes for numerator and denominator."""
        ff = self.font_frac()
        # A slot is "active" if tok itself is editing that part, or if editing_token is nested there
        def slot_active(part):
            if not tok.editing:
                return False
            if tok == editing_token:
                return tok.part == part
            # check if editing_token is nested in this part slot
            slot = tok.num if part == "num" else tok.den
            return self._tok_in_list(slot, editing_token)
        num_w, num_h = self._measure_slot(tok.num, slot_active("num"), ff)
        den_w, den_h = self._measure_slot(tok.den, slot_active("den"), ff)
        return num_w, num_h, den_w, den_h

    def _tok_in_list(self, tokens, target):
        """Return True if target is anywhere inside tokens (recursively)."""
        for t in tokens:
            if t is target:
                return True
            if isinstance(t, FracToken):
                for s in (t.num, t.den):
                    if self._tok_in_list(s, target):
                        return True
            elif isinstance(t, ExprToken):
                for s in t.slots:
                    if self._tok_in_list(s, target):
                        return True
        return False

    def _measure_slot(self, tokens, is_active_cursor_slot, font):
        """Measure a list of tokens, handling nested complex tokens properly.
        Zawsze mierzy token po tokenie (nie skleja stringów) — spójne z _draw_slot_tokens.
        """
        if not tokens:
            w, h = self.measure("□", font)
            return w, h
        total_w = 0
        max_h = 0
        # Use the same scale as the parent — slots render at full size.
        sub_scale = self.scale
        for t in tokens:
            if isinstance(t, str):
                tw, th = self.measure(t, font)
                total_w += tw
                max_h = max(max_h, th)
            elif isinstance(t, FracToken):
                sub_ff = ("Consolas", max(6, round(14 * sub_scale)), "bold")
                nw, nh = self._measure_slot(t.num, False, sub_ff)
                dw, dh = self._measure_slot(t.den, False, sub_ff)
                PAD = self.sp(6)
                SIDE_MARGIN = self.sp(4)
                fw = max(nw, dw) + PAD * 2 + SIDE_MARGIN * 2
                fh = nh + dh + self.sp(3) * 2   # 2 × BAR_GAP
                total_w += fw
                max_h = max(max_h, fh)
            elif isinstance(t, ExprToken):
                # Label uses font_frac size; main slot uses font_expr size
                lbl_ff  = ("Consolas", max(6, round(14 * sub_scale)), "bold")
                main_ff = ("Consolas", max(6, round(24 * sub_scale)), "bold")
                defn = EXPR_DEFS[t.kind]
                label_txt = defn[1]
                lw, lh = self.measure(label_txt, lbl_ff)
                sw, sh = self._measure_slot(t.slots[0], False, main_ff)
                total_w += lw + sw + self.sp(self.SLOT_PAD) * 2 + self.sp(10)
                max_h = max(max_h, sh + self.sp(self.SLOT_PAD))
        _, base_h = self.measure("0", font)
        return total_w or self.sp(20), max(max_h, base_h)

    def _draw_slot_tokens(self, tokens, active_frac_token, cursor_pos, x_start, cy, font):
        """Draw nested slot: either a sub-render or simple text.
        active_frac_token: the FracToken/ExprToken that is active in this context,
                           OR a deeper editing_token being propagated down (cursor_pos=None).
        cursor_pos: cursor index within this token list, or None when editing is deeper.
        """
        _, fh = self.measure("0", font)
        half_h = fh // 2
        is_active = active_frac_token is not None
        # Only collect cursor position at THIS level when cursor_pos is explicitly set;
        # when editing_token is nested deeper, cursor_pos is None and the cursor
        # will be collected by the sub-renderer at the correct deeper level.
        show_cursor = is_active and cursor_pos is not None

        if not tokens:
            # Empty slot: draw placeholder, highlight if active
            pw, ph = self.measure("□", font)
            if is_active:
                # filled highlight background
                self.cv.create_rectangle(
                    x_start - 2, cy - half_h - 2,
                    x_start + pw + 2, cy + half_h + 2,
                    fill="#003040", outline=ACCENT, width=1
                )
                if show_cursor:
                    self.cursor_positions.append((x_start, cy, half_h))
            self.cv.create_text(x_start, cy, text="□", font=font,
                                fill=ACCENT if is_active else FG_DIM, anchor="w")
            return

        # For nested FracToken/ExprToken inside a slot, do full sub-render
        # Use the SAME scale — slots must render at full size so that complex
        # tokens (fractions, functions) are not squished inside the parent slot.
        has_complex = any(isinstance(t, (FracToken, ExprToken)) for t in tokens)
        if has_complex:
            sub = Renderer(self.cv, self.scale, blink_visible=self.blink_visible)
            sub.draw_tokens(tokens, cursor_pos if is_active else None,
                            show_cursor, x_start, cy,
                            editing_token=active_frac_token)
            # Propagate collected cursor positions up
            self.cursor_positions.extend(sub.cursor_positions)
        else:
            # simple string tokens
            x = x_start
            for i, t in enumerate(tokens):
                if show_cursor and i == cursor_pos:
                    self.cursor_positions.append((x, cy, half_h))
                tw, _ = self.measure(t, font)
                self.cv.create_text(x, cy, text=t, font=font, fill=FG, anchor="w")
                x += tw
            if show_cursor and cursor_pos == len(tokens):
                self.cursor_positions.append((x, cy, half_h))

    # ── ExprToken ─────────────────────────────────────────────────────────────
    def _draw_expr(self, tok, x, cy, editing_token):
        kind     = tok.kind
        defn     = EXPR_DEFS[kind]
        label    = defn[1]
        style    = defn[2]
        SP       = self.sp(self.SLOT_PAD)
        GAP      = self.sp(2)
        ff_label = self.font_frac()   # small — for function labels
        fe       = self.font_expr()   # FULL SIZE — for main content slots
        fsup     = self.font_sup()    # small — for superscripts / subscripts
        _, lh    = self.measure("0", fe)
        _, sh    = self.measure("0", ff_label)

        def draw_slot(sx, sy, slot_tokens, is_active, use_font=None, slot_idx=0):
            """Draw a bordered slot box and its contents.
            use_font controls BOTH the box size and the text inside."""
            use_font = use_font or fe
            sw, sbh  = self._measure_slot(slot_tokens, is_active, use_font)
            box_w = sw + SP * 2
            box_h = sbh + SP
            bx0 = sx; by0 = sy - box_h // 2
            bx1 = sx + box_w; by1 = sy + box_h // 2
            clr      = ACCENT if is_active else FG_DIM
            fill_clr = "#003040" if is_active else ""
            self.cv.create_rectangle(bx0, by0, bx1, by1,
                                     outline=clr, fill=fill_clr, width=1)
            self.slot_hit_areas.append((tok, slot_idx, bx0, by0, bx1, by1))
            is_direct_edit = is_active and tok == editing_token
            if is_direct_edit:
                active_tok = tok
            elif is_active and editing_token is not None:
                active_tok = editing_token
            else:
                active_tok = None
            cur_pos = tok.cursor if is_direct_edit else None
            self._draw_slot_tokens(
                slot_tokens,
                active_tok,
                cur_pos,
                bx0 + SP, sy, use_font
            )
            return box_w

        def _tok_in_slot(slot, target_tok):
            for t in slot:
                if t is target_tok:
                    return True
                if isinstance(t, FracToken):
                    for s in (t.num, t.den):
                        if _tok_in_slot(s, target_tok):
                            return True
                elif isinstance(t, ExprToken):
                    for s in t.slots:
                        if _tok_in_slot(s, target_tok):
                            return True
            return False

        def is_slot_active(idx):
            if not tok.editing:
                return False
            if tok == editing_token and tok.slot_idx == idx:
                return True
            if editing_token is not None and editing_token is not tok:
                return _tok_in_slot(tok.slots[idx], editing_token)
            return False

        if style in ("prefix", "prefix_root"):
            lw, _ = self.measure(label, ff_label)
            self.cv.create_text(x + lw // 2, cy, text=label, font=ff_label, fill=FG, anchor="center")
            x += lw + GAP
            # Main slot at full font size
            sw = draw_slot(x, cy, tok.slots[0], is_slot_active(0), use_font=fe, slot_idx=0)
            return x + sw

        elif style == "abs":
            bar_w = self.sp(4)
            sw0, sh0 = self._measure_slot(tok.slots[0], is_slot_active(0), fe)
            box_h = sh0 + SP
            by0 = cy - box_h // 2; by1 = cy + box_h // 2
            clr = ACCENT if is_slot_active(0) else FG_DIM
            self.cv.create_line(x + bar_w // 2, by0, x + bar_w // 2, by1, fill=clr, width=2)
            x += bar_w + 1
            self.slot_hit_areas.append((tok, 0, x, by0, x + sw0, by1))
            is_direct_abs = is_slot_active(0) and tok == editing_token
            self._draw_slot_tokens(
                tok.slots[0],
                tok if is_direct_abs else (editing_token if is_slot_active(0) else None),
                tok.cursor if is_direct_abs else None,
                x, cy, fe
            )
            x += sw0 + 1
            self.cv.create_line(x + bar_w // 2, by0, x + bar_w // 2, by1, fill=clr, width=2)
            return x + bar_w + 1

        elif style == "postfix_fact":
            lw, _ = self.measure(label, ff_label)
            self.cv.create_text(x + lw // 2, cy, text=label, font=ff_label, fill=FG, anchor="center")
            x += lw + GAP
            sw = draw_slot(x, cy, tok.slots[0], is_slot_active(0), use_font=fe, slot_idx=0)
            x += sw
            ew, _ = self.measure("!", ff_label)
            self.cv.create_text(x + ew // 2, cy, text="!", font=ff_label, fill=FG, anchor="center")
            return x + ew

        elif style == "pow2":
            # Base slot at full size, superscript ² at small size
            sw = draw_slot(x, cy, tok.slots[0], is_slot_active(0), use_font=fe, slot_idx=0)
            x += sw
            supw, _ = self.measure("²", fsup)
            self.cv.create_text(x + supw // 2, cy - lh // 2, text="²",
                                 font=fsup, fill=FG, anchor="center")
            return x + supw

        elif style in ("pown", "prefix_exp", "prefix_sup"):
            # Base slot (or base label) at full size; exponent box at small size
            if style == "pown":
                sw0 = draw_slot(x, cy, tok.slots[0], is_slot_active(0), use_font=fe, slot_idx=0)
                x += sw0
                s1_tokens = tok.slots[1]
                active_s1 = is_slot_active(1)
                s1_idx    = 1
            else:
                base_label = "e" if style == "prefix_exp" else label
                ew, _ = self.measure(base_label, ff_label)
                self.cv.create_text(x + ew // 2, cy, text=base_label, font=ff_label, fill=FG, anchor="center")
                x += ew
                s1_tokens = tok.slots[0]
                active_s1 = is_slot_active(0)
                s1_idx    = 0

            sw1, sw1_h = self._measure_slot(s1_tokens, active_s1, fsup)
            box_w1  = sw1 + SP * 2
            box_h1  = sw1_h + SP
            bx0 = x; by0 = cy - lh // 2 - box_h1
            bx1 = x + box_w1; by1 = cy - lh // 2
            clr1  = ACCENT if active_s1 else FG_DIM
            fill1 = "#003040" if active_s1 else ""
            self.cv.create_rectangle(bx0, by0, bx1, by1, outline=clr1, fill=fill1, width=1)
            self.slot_hit_areas.append((tok, s1_idx, bx0, by0, bx1, by1))
            is_direct1 = active_s1 and tok == editing_token
            self._draw_slot_tokens(
                s1_tokens,
                tok if is_direct1 else (editing_token if active_s1 else None),
                tok.cursor if is_direct1 else None,
                bx0 + SP, (by0 + by1) // 2, fsup
            )
            return x + box_w1

        elif style == "xroot":
            # Small index box (superscript position), then √, then main slot full size
            sw0, sh0 = self._measure_slot(tok.slots[0], is_slot_active(0), fsup)
            box_w0 = sw0 + SP * 2; box_h0 = sh0 + SP
            bx0_0 = x; by0_0 = cy - lh // 2 - box_h0
            bx1_0 = x + box_w0; by1_0 = cy - lh // 2
            clr0  = ACCENT if is_slot_active(0) else FG_DIM
            fill0 = "#003040" if is_slot_active(0) else ""
            self.cv.create_rectangle(bx0_0, by0_0, bx1_0, by1_0, outline=clr0, fill=fill0, width=1)
            self.slot_hit_areas.append((tok, 0, bx0_0, by0_0, bx1_0, by1_0))
            is_direct0 = is_slot_active(0) and tok == editing_token
            self._draw_slot_tokens(
                tok.slots[0],
                tok if is_direct0 else (editing_token if is_slot_active(0) else None),
                tok.cursor if is_direct0 else None,
                bx0_0 + SP, (by0_0 + by1_0) // 2, fsup
            )
            x += box_w0
            sqw, _ = self.measure("√", ff_label)
            self.cv.create_text(x + sqw // 2, cy, text="√", font=ff_label, fill=FG, anchor="center")
            x += sqw + GAP
            # Main radicand slot at full size
            sw1 = draw_slot(x, cy, tok.slots[1], is_slot_active(1), use_font=fe, slot_idx=1)
            return x + sw1

        elif style == "prefix_sub":
            # "log" label at baseline, subscript box small, then main slot full size
            lw, llh = self.measure(label, ff_label)
            self.cv.create_text(x + lw // 2, cy, text=label, font=ff_label, fill=FG, anchor="center")
            x += lw
            sw0, sh0 = self._measure_slot(tok.slots[0], is_slot_active(0), fsup)
            box_w0 = sw0 + SP * 2
            box_h0 = sh0 + SP
            sub_top = cy + llh // 4
            bx0_s = x;          by0_s = sub_top
            bx1_s = x + box_w0; by1_s = sub_top + box_h0
            clr0  = ACCENT if is_slot_active(0) else FG_DIM
            fill0 = "#003040" if is_slot_active(0) else ""
            self.cv.create_rectangle(bx0_s, by0_s, bx1_s, by1_s, outline=clr0, fill=fill0, width=1)
            self.slot_hit_areas.append((tok, 0, bx0_s, by0_s, bx1_s, by1_s))
            is_direct = is_slot_active(0) and tok == editing_token
            self._draw_slot_tokens(
                tok.slots[0],
                tok if is_direct else (editing_token if is_slot_active(0) else None),
                tok.cursor if is_direct else None,
                bx0_s + SP, (by0_s + by1_s) // 2, fsup
            )
            x += box_w0 + GAP
            # Main argument slot at full size
            sw1 = draw_slot(x, cy, tok.slots[1], is_slot_active(1), use_font=fe, slot_idx=1)
            return x + sw1

        else:
            txt = label + "(" + (tokens_to_display_str(tok.slots[0]) or "□") + ")"
            tw, _ = self.measure(txt, fe)
            self.cv.create_text(x, cy, text=txt, font=fe, fill=FG, anchor="w")
            return x + tw

    def _slot_display(self, tokens, is_active, font):
        """Return (display_str, width, height) for a slot.
        For complex tokens (FracToken/ExprToken) use _measure_slot so the
        bounding box reflects their actual rendered size at current scale.
        """
        if not tokens:
            w, h = self.measure("□", font)
            return "□", w, h
        has_complex = any(isinstance(t, (FracToken, ExprToken)) for t in tokens)
        if has_complex:
            w, h = self._measure_slot(tokens, is_active, font)
            return "⬜", w, h
        s = "".join(t for t in tokens if isinstance(t, str)) or "□"
        w, h = self.measure(s, font)
        return s, w, h

    def _slot_display_dims(self, tokens, is_active, font):
        s, w, h = self._slot_display(tokens, is_active, font)
        return s, h, w



# ─── CURSOR-ONLY RENDERER ──────────────────────────────────────────────────────
class _CursorOnlyRenderer:
    """
    Walks the same token tree as Renderer but only draws the cursor line(s)
    for the currently active (editing) token. All canvas items are tagged
    "cursor" so they can be added/removed independently of the static content.
    """
    CURSOR_W = 2

    def __init__(self, canvas, scale):
        self.cv    = canvas
        self.scale = scale
        self._lbl_cache = {}

    def sp(self, n):
        return max(1, round(n * self.scale))

    def fs(self, base):
        return max(6, round(base * self.scale))

    def font_expr(self):  return ("Consolas", self.fs(24), "bold")
    def font_frac(self):  return ("Consolas", self.fs(14), "bold")
    def font_sup(self):   return ("Consolas", self.fs(11), "bold")

    def measure(self, text, font):
        key = (text, font)
        if key not in self._lbl_cache:
            lbl = tk.Label(self.cv, text=text, font=font, bg=DISP_BG, padx=0, pady=0)
            lbl.update_idletasks()
            w, h = lbl.winfo_reqwidth(), lbl.winfo_reqheight()
            lbl.destroy()
            self._lbl_cache[key] = (w, h)
        return self._lbl_cache[key]

    def _line(self, x, cy, half_h):
        item = self.cv.create_line(x, cy - half_h, x, cy + half_h,
                                   fill=ACCENT, width=self.CURSOR_W)
        self.cv.itemconfig(item, tags="cursor")

    def draw_cursor_nested(self, tokens, top_cursor, x_start, cy, editing_token):
        """Entry point: walk tokens at the top level to find where editing_token
        lives, then draw its cursor line."""
        if editing_token is None:
            return
        # Use a full Renderer pass with blink_visible=True to get accurate geometry,
        # but discard all drawn items — we only want the cursor positions.
        # Simpler: re-render with a shadow canvas... too complex.
        # Instead: use Renderer in blink=True mode on the real canvas,
        # collect cursor items by measuring before/after.
        # Simplest correct approach: just do a full render with blink=True
        # and delete non-cursor items afterward. But that flickers.
        #
        # Best approach given architecture: use Renderer(blink=True) which will
        # draw cursor lines mixed with tokens. Then move cursor-line items to
        # "cursor" tag and delete the rest. But we can't distinguish them.
        #
        # Cleanest solution: add a 'cursor_tag' param to Renderer so cursor lines
        # get a different tag. We implement that here minimally by subclassing.
        _CursorTagRenderer(self.cv, self.scale).draw_tokens(
            tokens, top_cursor, False, x_start, cy,
            editing_token=editing_token
        )


class _CursorTagRenderer(Renderer):
    """Like Renderer but ONLY draws cursor lines (tagged 'cursor').
    All other canvas drawing (text, rectangles, non-cursor lines) is
    suppressed so this renderer never overwrites the static content layer."""

    def __init__(self, canvas, scale):
        super().__init__(canvas, scale, blink_visible=True)

    # ── Suppress all non-cursor canvas drawing ────────────────────────────────
    # We monkey-patch the canvas methods temporarily so that inherited
    # _draw_frac / _draw_expr calls produce NO visual output — they just
    # walk the token tree to compute geometry (which we need for cursor pos).

    def _cursor_line(self, x, cy, half_h):
        """Emit one cursor line item tagged 'cursor'."""
        item = self._cv_create_line_real(
            x, cy - half_h, x, cy + half_h,
            fill=ACCENT, width=self.CURSOR_W
        )
        self.cv.itemconfig(item, tags="cursor")

    def draw_cursor_line(self, x, cy, half_h=None):
        """Called by inherited draw_tokens for top-level cursor position."""
        if not self.blink_visible:
            return
        if half_h is None:
            _, fh = self.measure("0", self.font_expr())
            half_h = fh // 2
        self._cursor_line(x, cy, half_h)

    def draw_tokens(self, tokens, cursor_pos, cursor_active, x, cy, editing_token=None):
        """Run full geometry walk with canvas drawing suppressed, then restore."""
        # Stash real canvas methods and replace with no-ops
        self._cv_create_text_real      = self.cv.create_text
        self._cv_create_rectangle_real = self.cv.create_rectangle
        self._cv_create_line_real      = self.cv.create_line

        self.cv.create_text      = lambda *a, **kw: None
        self.cv.create_rectangle = lambda *a, **kw: None
        # Lines are suppressed too; draw_cursor_line / _cursor_line bypass
        # this suppression by calling _cv_create_line_real directly.
        self.cv.create_line      = lambda *a, **kw: None

        try:
            return super().draw_tokens(tokens, cursor_pos, cursor_active, x, cy,
                                       editing_token=editing_token)
        finally:
            # Always restore real canvas methods
            self.cv.create_text      = self._cv_create_text_real
            self.cv.create_rectangle = self._cv_create_rectangle_real
            self.cv.create_line      = self._cv_create_line_real

    def _draw_slot_tokens(self, tokens, active_frac_token, cursor_pos, x_start, cy, font):
        """Walk slot tokens for geometry; only emit cursor lines."""
        _, fh = self.measure("0", font)
        half_h = fh // 2
        is_active = active_frac_token is not None
        show_cursor = is_active and cursor_pos is not None and self.blink_visible

        if not tokens:
            if show_cursor:
                self._cursor_line(x_start, cy, half_h)
            return

        has_complex = any(isinstance(t, (FracToken, ExprToken)) for t in tokens)
        if has_complex:
            sub = _CursorTagRenderer(self.cv, self.scale)
            sub.draw_tokens(tokens, cursor_pos if is_active else None,
                            show_cursor, x_start, cy,
                            editing_token=active_frac_token)
        else:
            x = x_start
            for i, t in enumerate(tokens):
                if show_cursor and i == cursor_pos:
                    self._cursor_line(x, cy, half_h)
                tw, _ = self.measure(t, font)
                x += tw
            if show_cursor and cursor_pos == len(tokens):
                self._cursor_line(x, cy, half_h)


# ─── WYŚWIETLACZ TOKENOWY + SCROLL + ZOOM ─────────────────────────────────────
class ExprDisplay(tk.Frame):
    """
    Frame containing:
      - a Canvas for drawing the expression (scrollable, zoomable)
      - H scrollbar
      - V scrollbar (shared with result frame or hidden when not needed)
    The result label is drawn BELOW the expression canvas, inside same bg frame.
    Ctrl+Plus / Ctrl+Minus / Ctrl+0 zoom in/out/reset.
    """
    SCALE_MIN  = 0.4
    SCALE_MAX  = 3.0
    SCALE_STEP = 0.15
    SCALE_DEF  = 1.0
    CANVAS_BASE_H = 130  # base height at scale=1

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=DISP_BG, **kw)

        self._tokens        = []
        self._cursor        = 0
        self._scale         = self.SCALE_DEF
        self._blink_visible = True
        self._blink_id      = None
        self._editing_token = None
        self._rects         = []
        self._slot_hit_areas = []   # [(tok, slot_spec, x0, y0, x1, y1)]
        self._in_redraw     = False
        self._configure_after_id = None

        # Selection: token-index range [_sel_a, _sel_b) in _rects.
        # Both None = no selection.
        self._sel_a         = None
        self._sel_b         = None

        # Callback wired by Calculator
        self.on_click_pos   = None   # fn(gap_idx, mx) — gap cursor position

        self._canvas = tk.Canvas(self, bg=DISP_BG, highlightthickness=0,
                                 scrollregion=(0, 0, 2000, 200))
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._canvas.bind("<Button-1>",       self._on_press)
        self._canvas.bind("<Configure>",      self._on_canvas_configure)
        self._start_blink()

    def attach_scrollbars(self, hbar, vbar):
        """Wire externally-created scrollbars to this canvas."""
        self._canvas.configure(
            xscrollcommand=hbar.set,
            yscrollcommand=vbar.set,
        )
        hbar.configure(command=self._canvas.xview)
        vbar.configure(command=self._canvas.yview)

    # ── Canvas Configure debounce ──────────────────────────────────────────────
    def _on_canvas_configure(self, event):
        """Debounce <Configure> so rapid cascades collapse into one _redraw."""
        if self._configure_after_id is not None:
            self.after_cancel(self._configure_after_id)
        self._configure_after_id = self.after(30, self._on_configure_fire)

    def _on_configure_fire(self):
        self._configure_after_id = None
        self._redraw()

    # ── Public API ─────────────────────────────────────────────────────────────
    def set_tokens(self, tokens, cursor=None, editing_token=None,
                   sel_a=None, sel_b=None):
        self._tokens = tokens
        self._editing_token = editing_token
        if cursor is None:
            self._cursor = len(tokens)
        else:
            self._cursor = max(0, min(len(tokens), cursor))
        self._sel_a = sel_a
        self._sel_b = sel_b
        self._blink_visible = True
        self._redraw()

    def get_cursor(self): return self._cursor

    def set_cursor(self, pos):
        self._cursor = max(0, min(len(self._tokens), pos))
        self._blink_visible = True
        self._redraw()

    def zoom_in(self):
        self._scale = min(self.SCALE_MAX, self._scale + self.SCALE_STEP)
        self._redraw()

    def zoom_out(self):
        self._scale = max(self.SCALE_MIN, self._scale - self.SCALE_STEP)
        self._redraw()

    def zoom_reset(self):
        self._scale = self.SCALE_DEF
        self._redraw()

    # ── Drawing ────────────────────────────────────────────────────────────────
    def _redraw(self):
        """Full redraw: static content + cursor."""
        if self._in_redraw:
            return
        self._in_redraw = True
        try:
            self._do_redraw_static()
            self._do_redraw_cursor()
        finally:
            self._in_redraw = False

    def _do_redraw_static(self):
        """Draw everything except the cursor (tokens, slots, highlights).
        Called on every full redraw and whenever tokens/state change."""
        cv = self._canvas
        cv.delete("all")

        cw = cv.winfo_width()  or 800
        ch = cv.winfo_height() or int(self.CANVAS_BASE_H * self._scale)

        renderer = Renderer(cv, self._scale, blink_visible=False)

        vpad   = renderer.sp(renderer.PAD_Y)
        expr_h = self._estimate_expr_height(renderer, self._tokens)

        above_axis = expr_h // 2
        draw_h = max(ch, expr_h + vpad * 2)
        cy = max(above_axis + vpad, draw_h // 2)
        self._draw_cy = cy
        self._draw_renderer_scale = self._scale

        x_start = renderer.sp(renderer.PAD_X)
        self._draw_x_start = x_start

        # Selection highlight
        if (self._sel_a is not None and self._sel_b is not None
                and self._sel_a < self._sel_b
                and self._rects
                and self._sel_b <= len(self._rects)):
            rx0 = self._rects[self._sel_a][0]
            rx1 = self._rects[self._sel_b - 1][1]
            sel_h = max(expr_h, renderer.sp(renderer.BASE_EXPR)) + vpad
            cv.create_rectangle(
                rx0 - 2, cy - sel_h // 2,
                rx1 + 2, cy + sel_h // 2,
                fill="#1a4060", outline=ACCENT, width=1
            )

        new_x, self._rects = renderer.draw_tokens(
            self._tokens, self._cursor, False, x_start, cy,
            editing_token=self._editing_token
        )
        self._slot_hit_areas = renderer.slot_hit_areas

        content_w = max(new_x + renderer.sp(renderer.PAD_X), cw)
        content_h = max(draw_h, ch)
        new_sr = (0, 0, content_w, content_h)
        if getattr(self, "_last_scrollregion", None) != new_sr:
            self._last_scrollregion = new_sr
            cv.configure(scrollregion=new_sr)

        if new_x > cw:
            cv.xview_moveto(max(0.0, (new_x - cw * 0.8)) / content_w)

    def _do_redraw_cursor(self):
        """Draw (or hide) only the cursor/caret using the 'cursor' canvas tag."""
        cv = self._canvas
        # Remove old cursor items (tagged "cursor")
        for item in cv.find_withtag("cursor"):
            cv.delete(item)

        if not self._blink_visible:
            return
        if not hasattr(self, "_draw_cy"):
            return

        cy    = self._draw_cy
        scale = self._draw_renderer_scale
        x_start = self._draw_x_start

        any_editing   = self._editing_token is not None
        cursor_active = not any_editing

        renderer = Renderer(cv, scale, blink_visible=True)

        if cursor_active:
            # Top-level cursor — draw between token rects
            _, fh = renderer.measure("0", renderer.font_expr())
            half_h = fh // 2
            if self._cursor <= len(self._rects) and self._rects:
                if self._cursor < len(self._rects):
                    cx_x = self._rects[self._cursor][0]
                else:
                    cx_x = self._rects[-1][1]
            else:
                cx_x = x_start
            item = cv.create_line(cx_x, cy - half_h, cx_x, cy + half_h,
                                  fill=ACCENT, width=renderer.CURSOR_W)
            cv.itemconfig(item, tags="cursor")
        else:
            # Nested cursor — use a CursorOnlyRenderer that only draws cursor lines
            cur_renderer = _CursorOnlyRenderer(cv, scale)
            cur_renderer.draw_cursor_nested(
                self._tokens, self._cursor, x_start, cy,
                self._editing_token
            )

    def _estimate_expr_height(self, renderer, tokens):
        """Estimate pixel height of a token list (for scrollregion / centring).
        Returns total pixel height of the expression.
        The math axis (cy) sits at above_axis pixels from the top.
        For simple text the axis sits at mid-height, so above=below=fh//2.
        """
        _, base_fh = renderer.measure("0", renderer.font_expr())
        _, frac_fh = renderer.measure("0", renderer.font_frac())
        above = base_fh // 2
        below = base_fh // 2
        BAR_GAP = renderer.sp(3)
        for tok in tokens:
            if isinstance(tok, FracToken):
                num_tokens = tok.num if tok.num else []
                den_tokens = tok.den if tok.den else []
                # _measure_slot returns (w, h) — use h for each slot
                ff = renderer.font_frac()
                nw, nh = renderer._measure_slot(num_tokens, False, ff) if num_tokens else renderer.measure("□", ff)
                dw, dh = renderer._measure_slot(den_tokens, False, ff) if den_tokens else renderer.measure("□", ff)
                # num sits above the bar: BAR_GAP + full numerator height
                tok_above = BAR_GAP + nh
                # den sits below the bar: BAR_GAP + full denominator height
                tok_below = BAR_GAP + dh
                above = max(above, tok_above)
                below = max(below, tok_below)
            elif isinstance(tok, ExprToken):
                ff = renderer.font_frac()
                for slot in tok.slots:
                    if slot:
                        sw, sh = renderer._measure_slot(slot, False, ff)
                    else:
                        sw, sh = renderer.measure("□", ff)
                    slot_half = sh // 2 + renderer.sp(renderer.SLOT_PAD)
                    above = max(above, slot_half)
                    below = max(below, slot_half)
        return above + below

    def _start_blink(self):
        self._blink_id = self.after(530, self._blink)

    def _blink(self):
        self._blink_visible = not self._blink_visible
        # Only redraw the cursor layer — static content stays untouched
        if not self._in_redraw:
            self._do_redraw_cursor()
        self._blink_id = self.after(530, self._blink)

    # ── Mouse helpers ──────────────────────────────────────────────────────────
    def _mx_to_tok_idx(self, ev_x):
        """Convert canvas pixel x → token index (0..len-1) or -1 if before all."""
        mx = self._canvas.canvasx(ev_x)
        for i, (x0, x1) in enumerate(self._rects):
            if mx <= x1:
                return i
        return len(self._rects) - 1 if self._rects else -1

    def _mx_to_gap(self, ev_x):
        """Convert canvas pixel x → gap index (0..len), i.e. cursor position."""
        mx = self._canvas.canvasx(ev_x)
        best_i = len(self._tokens)
        for i, (x0, x1) in enumerate(self._rects):
            if x0 <= mx <= x1:
                mid = (x0 + x1) // 2
                best_i = i if mx < mid else i + 1
                break
            elif mx < x0:
                best_i = i
                break
        return best_i

    def _hit_slot(self, ev_x, ev_y):
        """Check if (ev_x, ev_y) falls inside any slot hit area.
        Returns (tok, slot_spec) or (None, None)."""
        mx = self._canvas.canvasx(ev_x)
        my = self._canvas.canvasy(ev_y)
        # Iterate in reverse so topmost/most-nested slots take priority
        for tok, slot_spec, x0, y0, x1, y1 in reversed(self._slot_hit_areas):
            if x0 <= mx <= x1 and y0 <= my <= y1:
                return tok, slot_spec
        return None, None

    def _on_press(self, ev):
        gap     = self._mx_to_gap(ev.x)
        self._sel_a = None
        self._sel_b = None
        self._cursor = gap
        self._blink_visible = True
        # Check if click landed inside a nested slot (FracToken num/den or ExprToken slot)
        slot_tok, slot_spec = self._hit_slot(ev.x, ev.y)
        if self.on_click_pos:
            self.on_click_pos(gap, self._mx_to_tok_idx(ev.x), self._canvas.canvasx(ev.x),
                              slot_tok, slot_spec)
        self._redraw()
        self._redraw()



# ─── KALKULATOR ───────────────────────────────────────────────────────────────
class Calculator:
    def __init__(self, root):
        self.root     = root
        self.deg_mode = True
        self.memory   = 0.0
        self.history  = []
        self.hist_i   = 0
        self._deg_btn = None

        self._tokens  = []    # top-level token list
        self._cursor  = 0     # cursor in top-level list

        # Selection (always in top-level list for now)
        self._sel_a   = None  # inclusive start index
        self._sel_b   = None  # exclusive end index

        # Navigation stack: list of (token, part_or_slot_idx)
        # When we enter a FracToken slot or ExprToken slot, we push the context.
        # (token, "num"/"den") for FracToken
        # (token, 0/1) for ExprToken
        self._nav_stack = []  # [(token, slot_spec)]
        # Currently editing token (top of stack or None)
        self._active = None   # FracToken | ExprToken | None

        root.title("Kalkulator Naukowy")
        root.configure(bg="#000000")
        root.resizable(True, True)
        self._build()

    # ── active slot helpers ────────────────────────────────────────────────────
    def _active_slot(self):
        """Return (token_list, cursor_pos) for the currently active editing context."""
        if self._active is None:
            return self._tokens, self._cursor
        if isinstance(self._active, FracToken):
            ft = self._active
            sl = ft.num if ft.part == "num" else ft.den
            return sl, ft.cursor
        elif isinstance(self._active, ExprToken):
            et = self._active
            return et.slots[et.slot_idx], et.cursor

    def _set_active_cursor(self, pos):
        if self._active is None:
            self._cursor = pos
        elif isinstance(self._active, FracToken):
            self._active.cursor = pos
        elif isinstance(self._active, ExprToken):
            self._active.cursor = pos

    def _get_active_cursor(self):
        if self._active is None:
            return self._cursor
        elif isinstance(self._active, FracToken):
            return self._active.cursor
        elif isinstance(self._active, ExprToken):
            return self._active.cursor

    def _enter_token(self, tok, from_right=True):
        """Enter a FracToken or ExprToken from the outside."""
        if isinstance(tok, FracToken):
            tok.editing = True
            if from_right:
                tok.part = "den"
                tok.cursor = len(tok.den)
            else:
                tok.part = "num"
                tok.cursor = 0
            self._active = tok
        elif isinstance(tok, ExprToken):
            tok.editing = True
            if from_right:
                n = 2 if tok.two_slots else 1
                tok.slot_idx = n - 1
                tok.cursor = len(tok.slots[tok.slot_idx])
            else:
                tok.slot_idx = 0
                tok.cursor = 0
            self._active = tok

    def _exit_token(self, to_right):
        """Exit the currently active token back to parent context."""
        tok = self._active
        tok.editing = False

        # First check top-level list
        for i, t in enumerate(self._tokens):
            if t is tok:
                self._active = None
                self._cursor = i + 1 if to_right else i
                return

        # Token is nested inside another token's slot — find the parent
        parent = self._find_parent(self._tokens, tok)
        if parent is not None:
            self._active = parent
            parent.editing = True
            # Mark all ancestors up to top-level as editing=True so the renderer
            # activates their slot highlights along the whole nesting chain
            ancestor = self._find_parent(self._tokens, parent)
            while ancestor is not None:
                ancestor.editing = True
                ancestor = self._find_parent(self._tokens, ancestor)
            if isinstance(parent, FracToken):
                slot = parent.num if parent.part == "num" else parent.den
                try:
                    idx = next(i for i, t in enumerate(slot) if t is tok)
                    parent.cursor = idx + 1 if to_right else idx
                except StopIteration:
                    parent.cursor = len(slot) if to_right else 0
            elif isinstance(parent, ExprToken):
                # Find which slot actually contains tok (don't assume parent.slot_idx)
                found = False
                for si, slot in enumerate(parent.slots):
                    for i, t in enumerate(slot):
                        if t is tok:
                            parent.slot_idx = si
                            parent.cursor = i + 1 if to_right else i
                            found = True
                            break
                    if found:
                        break
                if not found:
                    parent.cursor = len(parent.slots[parent.slot_idx]) if to_right else 0
        else:
            # fallback
            self._active = None
            self._cursor = len(self._tokens)

    def _find_parent(self, tokens, target):
        """Recursively find the FracToken/ExprToken that directly contains target in a slot."""
        for t in tokens:
            if isinstance(t, FracToken):
                for slot in (t.num, t.den):
                    if any(s is target for s in slot):
                        return t
                    result = self._find_parent(slot, target)
                    if result is not None:
                        return result
            elif isinstance(t, ExprToken):
                for slot in t.slots:
                    if any(s is target for s in slot):
                        return t
                    result = self._find_parent(slot, target)
                    if result is not None:
                        return result
        return None

    # ── Right-operand collection ───────────────────────────────────────────────
    def _collect_right_operand(self, slot, cursor):
        """Return the list of tokens that form a single operand immediately to
        the right of `cursor` in `slot`, or [] if there is nothing collectable.

        Rules:
        - If the token at cursor is a FracToken or ExprToken → return [that token].
        - If the token at cursor is a string that opens a parenthesised group
          (i.e. it is exactly "(") → collect everything up to and including the
          matching closing ")", returning all those string tokens.
        - Otherwise (plain number/symbol string) → collect that single token.
        """
        if cursor >= len(slot):
            return []
        tok = slot[cursor]
        if isinstance(tok, (FracToken, ExprToken)):
            return [tok]
        if isinstance(tok, str):
            if tok == "(":
                # collect until matching ")"
                depth = 0
                end = cursor
                for i in range(cursor, len(slot)):
                    t = slot[i]
                    if isinstance(t, str):
                        for ch in t:
                            if ch == "(":
                                depth += 1
                            elif ch == ")":
                                depth -= 1
                    if depth == 0:
                        end = i
                        break
                return list(slot[cursor:end + 1])
            else:
                return [tok]
        return []

    # ── Left-operand collection ────────────────────────────────────────────────
    # Characters that are operators / separators — a run of these is NOT an operand.
    _OPERATORS = set("+-*/÷×−%")

    def _collect_left_operand(self, slot, cursor):
        """Return (tokens, start_index) for the operand immediately to the LEFT
        of `cursor` in `slot`, or ([], cursor) if nothing collectable.

        An "operand" to the left is one of:
        - A single FracToken or ExprToken immediately left of cursor.
        - A closing-parenthesis group  "( ... )"  immediately left of cursor.
        - A contiguous run of number/symbol string-tokens (digits, '.', pi,
          epsilon, phi, 'e', constants -- anything that is NOT a pure operator
          character and NOT an opening paren).  The run is collected backwards
          until we hit an operator, an opening paren, a FracToken, or an
          ExprToken.

        Operators (+ - * / div x %) and "(" are NOT collected.
        """
        if cursor <= 0:
            return [], cursor
        left = slot[cursor - 1]

        # FracToken / ExprToken
        if isinstance(left, (FracToken, ExprToken)):
            return [left], cursor - 1

        # Closing-paren group
        if isinstance(left, str) and left == ")":
            depth = 0
            start = cursor - 1
            for i in range(cursor - 1, -1, -1):
                t = slot[i]
                if isinstance(t, str):
                    for ch in reversed(t):
                        if ch == ")":
                            depth += 1
                        elif ch == "(":
                            depth -= 1
                if depth == 0:
                    start = i
                    break
            return list(slot[start:cursor]), start

        # Run of number / symbol string-tokens
        if isinstance(left, str):
            def _is_number_like(t):
                if not isinstance(t, str):
                    return False
                if t in ("(", ")"):
                    return False
                if all(c in self._OPERATORS for c in t):
                    return False
                return True

            if not _is_number_like(left):
                return [], cursor

            start = cursor - 1
            while start > 0 and _is_number_like(slot[start - 1]):
                start -= 1
            return list(slot[start:cursor]), start

        return [], cursor

    # ── build UI ──────────────────────────────────────────────────────────────
    def _build(self):
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0, minsize=800)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = tk.Frame(self.root, bg="#000000")
        main_frame.grid(row=0, column=1, sticky="nsew")
        # row 0 = accent bar (fixed), row 1 = display panel (fixed height),
        # row 2 = button grid (expands)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=0)
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)

        tk.Frame(main_frame, bg=ACCENT, height=4).grid(row=0, column=0, sticky="ew")

        disp = tk.Frame(main_frame, bg=DISP_BG, height=140)
        disp.grid(row=1, column=0, sticky="ew")
        disp.grid_propagate(False)

        def _resize_disp(event, _disp=disp, _main=main_frame):
            # cell size when buttons are square = width/10
            # buttons area height = 6 * cell = 6 * (width/10) = 0.6 * width
            # display height = total_height - accent(4) - buttons_area - padding(12)
            total_h = event.height
            width   = event.width
            cell    = max(60, width // 10)
            btn_h   = cell * 6 + 12   # 6 rows + padding
            dh      = max(80, total_h - btn_h - 4)
            _disp.config(height=dh)
        main_frame.bind("<Configure>", _resize_disp)
        # disp grid:  row0=top_row  row1=canvas+vbar  row2=hbar  row3=res
        #             col0=content  col1=vbar
        disp.rowconfigure(1, weight=1)
        disp.columnconfigure(0, weight=1)

        top_row = tk.Frame(disp, bg=DISP_BG)
        top_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(6, 0))
        self.mode_lbl = tk.Label(top_row, text="Deg", bg=DISP_BG, fg=FG_DIM,
                                  font=("Consolas", 11, "bold"))
        self.mode_lbl.pack(side="right")

        # Dark ttk scrollbar style (works on Windows where tk.Scrollbar ignores colours)
        _style = ttk.Style()
        _style.theme_use("default")
        _style.configure("Dark.Horizontal.TScrollbar",
                         background="#555555", troughcolor="#1a1a1a",
                         bordercolor="#1a1a1a", arrowcolor="#444444",
                         darkcolor="#484848", lightcolor="#626262",
                         relief="flat", borderwidth=0,
                         width=12, arrowsize=12)
        _style.configure("Dark.Vertical.TScrollbar",
                         background="#555555", troughcolor="#1a1a1a",
                         bordercolor="#1a1a1a", arrowcolor="#444444",
                         darkcolor="#484848", lightcolor="#626262",
                         relief="flat", borderwidth=0,
                         width=12, arrowsize=12)
        _style.map("Dark.Horizontal.TScrollbar",
                   background=[("active", "#666666"), ("pressed", "#777777")],
                   arrowcolor=[("active", "#666666"), ("pressed", "#777777")])
        _style.map("Dark.Vertical.TScrollbar",
                   background=[("active", "#666666"), ("pressed", "#777777")],
                   arrowcolor=[("active", "#666666"), ("pressed", "#777777")])

        # ExprDisplay — pure canvas, no internal scrollbars
        self.expr_disp = ExprDisplay(disp)
        self.expr_disp.grid(row=1, column=0, sticky="nsew")

        # Wire mouse callback
        self.expr_disp.on_click_pos  = self._on_display_click

        # Scrollbars are siblings of ExprDisplay inside disp,
        # so their appearance/disappearance never resizes the canvas
        _hbar = ttk.Scrollbar(disp, orient="horizontal",
                              style="Dark.Horizontal.TScrollbar")
        _vbar = ttk.Scrollbar(disp, orient="vertical",
                              style="Dark.Vertical.TScrollbar")
        self.expr_disp.attach_scrollbars(_hbar, _vbar)

        # Auto-show scrollbars only when content overflows
        _hbar_visible = [False]
        _vbar_visible = [False]

        def _on_hscroll(lo, hi):
            lo, hi = float(lo), float(hi)
            if lo <= 0.0 and hi >= 1.0:
                if _hbar_visible[0]:
                    _hbar.grid_remove()
                    _hbar_visible[0] = False
            else:
                if not _hbar_visible[0]:
                    _hbar.grid(row=2, column=0, sticky="ew")
                    _hbar_visible[0] = True
            _hbar.set(lo, hi)

        def _on_vscroll(lo, hi):
            lo, hi = float(lo), float(hi)
            if lo <= 0.0 and hi >= 1.0:
                if _vbar_visible[0]:
                    _vbar.grid_remove()
                    _vbar_visible[0] = False
            else:
                if not _vbar_visible[0]:
                    _vbar.grid(row=1, column=1, sticky="ns")
                    _vbar_visible[0] = True
            _vbar.set(lo, hi)

        self.expr_disp._canvas.configure(
            xscrollcommand=_on_hscroll,
            yscrollcommand=_on_vscroll,
        )

        # Result label
        res_frame = tk.Frame(disp, bg=DISP_BG)
        res_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 8))
        self.res_lbl = tk.Label(res_frame, text="", bg=DISP_BG, fg=FG_DIM,
                                 font=("Consolas", 14, "bold"), anchor="e", justify="right")
        self.res_lbl.pack(fill="x")

        self._res_frac_cv  = None
        self._res_frac_vis = False

        # Keyboard grid — pack so _make_square receives correct width+height
        kf = tk.Frame(main_frame, bg="#000000", bd=0, highlightthickness=0)
        kf.grid(row=2, column=0, sticky="nsew", pady=(4, 4), padx=4)
        for c in range(10):
            kf.columnconfigure(c, weight=1, uniform="btn", minsize=60)
        for rw in range(6):
            kf.rowconfigure(rw, weight=1, uniform="btn", minsize=60)

        def _make_square(event, _kf=kf):
            cell = max(60, min(event.width // 10, event.height // 6))
            for c in range(10):
                _kf.columnconfigure(c, weight=1, uniform="btn", minsize=cell)
            for rw in range(6):
                _kf.rowconfigure(rw, weight=1, uniform="btn", minsize=cell)
        kf.bind("<Configure>", _make_square)

        I  = self._ins
        IE = self._ins_expr
        IF = self._frac_new

        btns = [
            ("(",       0,0,1, BTN_DARK,  lambda: I("(")),
            (")",       1,0,1, BTN_DARK,  lambda: I(")")),
            ("□\n─\n□", 2,0,1, BTN_DARK,  IF),
            ("³√",      3,0,1, BTN_DARK,  lambda: IE("cbrt")),
            ("▲",       4,0,1, BTN_BLUE,  self._arrow_up),
            ("Deg",     5,0,1, BTN_DARK,  self._toggle_angle),
            ("C",       6,0,1, BTN_RED,   self._clear),
            ("M",       7,0,1, BTN_DARK,  self._mem_recall),
            ("Dec",     8,0,1, BTN_TEAL,  lambda: None),
            ("⌫",       9,0,1, BTN_RED,   self._back),
            ("(□)",     0,1,1, BTN_DARK,  lambda: IE("abs")),
            ("log_□□",  1,1,1, BTN_DARK,  lambda: IE("loga")),
            ("10𐞄",     2,1,1, BTN_DARK,  lambda: IE("pow10")),
            ("◄",       3,1,1, BTN_BLUE,  self._cur_left),
            ("▼",       4,1,1, BTN_BLUE,  self._arrow_down),
            ("►",       5,1,1, BTN_BLUE,  self._cur_right),
            ("𐞄√",      6,1,1, BTN_DARK,  lambda: IE("xroot")),
            ("Mod",     7,1,1, BTN_DARK,  lambda: I("%")),
            ("X",       8,1,1, BTN_DARK,  lambda: I("*")),
            ("÷",       9,1,1, BTN_DARK,  lambda: I("÷")),
            ("|□|",     0,2,1, BTN_DARK,  lambda: IE("abs")),
            ("n!",      1,2,1, BTN_DARK,  lambda: IE("factorial")),
            ("x²",      2,2,1, BTN_DARK,  lambda: IE("pow2")),
            ("x𐞄",      3,2,1, BTN_DARK,  lambda: IE("pown")),
            ("e𐞄",      4,2,1, BTN_DARK,  lambda: IE("exp")),
            ("e",       5,2,1, BTN_DARK,  lambda: I("e")),
            ("7",       6,2,1, BTN_MED,   lambda: I("7")),
            ("8",       7,2,1, BTN_MED,   lambda: I("8")),
            ("9",       8,2,1, BTN_MED,   lambda: I("9")),
            ("*",       9,2,1, BTN_DARK,  lambda: I("*")),
            ("√",       0,3,1, BTN_DARK,  lambda: IE("sqrt")),
            ("sin",     1,3,1, BTN_DARK,  lambda: IE("sin")),
            ("cos",     2,3,1, BTN_DARK,  lambda: IE("cos")),
            ("tan",     3,3,1, BTN_DARK,  lambda: IE("tan")),
            ("cot",     4,3,1, BTN_DARK,  lambda: IE("cot")),
            ("π",       5,3,1, BTN_DARK,  lambda: I("π")),
            ("4",       6,3,1, BTN_MED,   lambda: I("4")),
            ("5",       7,3,1, BTN_MED,   lambda: I("5")),
            ("6",       8,3,1, BTN_MED,   lambda: I("6")),
            ("−",       9,3,1, BTN_DARK,  lambda: I("−")),
            ("lg",      0,4,1, BTN_DARK,  lambda: IE("lg")),
            ("asin",    1,4,1, BTN_DARK,  lambda: IE("asin")),
            ("acos",    2,4,1, BTN_DARK,  lambda: IE("acos")),
            ("atan",    3,4,1, BTN_DARK,  lambda: IE("atan")),
            ("acot",    4,4,1, BTN_DARK,  lambda: IE("acot")),
            ("ε",       5,4,1, BTN_DARK,  lambda: I("ε")),
            ("1",       6,4,1, BTN_MED,   lambda: I("1")),
            ("2",       7,4,1, BTN_MED,   lambda: I("2")),
            ("3",       8,4,1, BTN_MED,   lambda: I("3")),
            ("+",       9,4,1, BTN_DARK,  lambda: I("+")),
            ("ln",      0,5,1, BTN_DARK,  lambda: IE("ln")),
            ("sinh",    1,5,1, BTN_DARK,  lambda: IE("sinh")),
            ("cosh",    2,5,1, BTN_DARK,  lambda: IE("cosh")),
            ("tanh",    3,5,1, BTN_DARK,  lambda: IE("tanh")),
            ("coth",    4,5,1, BTN_DARK,  lambda: IE("coth")),
            ("φ",       5,5,1, BTN_DARK,  lambda: I("φ")),
            ("0",       6,5,2, BTN_MED,   lambda: I("0")),
            (".",       8,5,1, BTN_PURP,  lambda: I(".")),
            ("=",       9,5,1, BTN_TEAL,  self._calc),
        ]

        for txt, col, row, cs, color, cmd in btns:
            if txt in ["7","8","9","4","5","6","1","2","3","0",".",
                       "=","+","−","*","÷","X","Mod","C","⌫","(",")"]:
                b_font = ("Consolas", 22, "bold")
            elif len(txt) >= 4:
                b_font = ("Consolas", 11, "bold")
            else:
                b_font = ("Consolas", 13, "bold")

            # Use Frame+Label instead of Button to get sharp rectangular corners
            # on all platforms (Windows tk.Button ignores relief="flat" for corners)
            frm = tk.Frame(kf, bg=color, bd=0, highlightthickness=0)
            frm.grid(row=row, column=col, columnspan=cs,
                     sticky="nsew", padx=4, pady=4)
            lbl = tk.Label(
                frm, text=txt, bg=color, fg=FG,
                font=b_font,
                cursor="hand2",
                anchor="center",
            )
            lbl.place(relx=0, rely=0, relwidth=1, relheight=1)

            def _bind_btn(f, l, c, fn):
                l.bind("<Enter>",          lambda e, w=f, x=l, cl=c: (w.config(bg=self._lighter(cl)), x.config(bg=self._lighter(cl))))
                l.bind("<Leave>",          lambda e, w=f, x=l, cl=c: (w.config(bg=cl), x.config(bg=cl)))
                l.bind("<ButtonPress-1>",  lambda e, w=f, x=l, cl=c: (w.config(bg=self._lighter(self._lighter(cl))), x.config(bg=self._lighter(self._lighter(cl)))))
                l.bind("<ButtonRelease-1>",lambda e, w=f, x=l, cl=c, fn=fn: (w.config(bg=self._lighter(cl)), x.config(bg=self._lighter(cl)), fn()))
                f.bind("<ButtonPress-1>",  lambda e, w=f, x=l, cl=c: (w.config(bg=self._lighter(self._lighter(cl))), x.config(bg=self._lighter(self._lighter(cl)))))
                f.bind("<ButtonRelease-1>",lambda e, w=f, x=l, cl=c, fn=fn: (w.config(bg=self._lighter(cl)), x.config(bg=self._lighter(cl)), fn()))
            _bind_btn(frm, lbl, color, cmd)

            if txt == "Deg":
                self._deg_btn = lbl
                self._deg_frm = frm

        # Key bindings on root — force focus to root so keys always work
        self.root.bind("<Key>",      self._on_key)
        self.root.bind("<Return>",   lambda e: self._calc())
        self.root.bind("<KP_Enter>", lambda e: self._calc())
        self.root.bind("<BackSpace>",lambda e: self._back())
        self.root.bind("<Escape>",   lambda e: self._clear())
        self.root.bind("<Left>",     lambda e: (self._cur_left(), "break"))
        self.root.bind("<Right>",    lambda e: (self._cur_right(), "break"))
        self.root.bind("<Up>",       lambda e: (self._arrow_up(), "break"))
        self.root.bind("<Down>",     lambda e: (self._arrow_down(), "break"))
        # Keep focus on root so keyboard input is never swallowed by buttons
        self.root.bind("<FocusOut>", lambda e: self.root.after(10, lambda: self.root.focus_set()))
        self.root.after(100, self.root.focus_set)
        # Zoom
        self.root.bind("<Control-equal>",   lambda e: self.expr_disp.zoom_in())
        self.root.bind("<Control-plus>",    lambda e: self.expr_disp.zoom_in())
        self.root.bind("<Control-minus>",   lambda e: self.expr_disp.zoom_out())
        self.root.bind("<Control-0>",       lambda e: self.expr_disp.zoom_reset())
        self.root.bind("<Control-KP_Add>",  lambda e: self.expr_disp.zoom_in())
        self.root.bind("<Control-KP_Subtract>", lambda e: self.expr_disp.zoom_out())

    @staticmethod
    def _lighter(hex_col):
        h = hex_col.lstrip("#")
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return "#{:02x}{:02x}{:02x}".format(
            min(r+25,255), min(g+25,255), min(b+25,255))

    # ── Selection helpers ──────────────────────────────────────────────────────
    def _clear_sel(self):
        self._sel_a = None
        self._sel_b = None

    def _has_sel(self):
        return (self._sel_a is not None and self._sel_b is not None
                and self._sel_b > self._sel_a)

    def _sel_tokens(self):
        """Return a COPY of the selected token sublist."""
        if not self._has_sel():
            return []
        return list(self._tokens[self._sel_a:self._sel_b])

    def _delete_sel(self):
        """Remove selected tokens from top-level list, set cursor to sel_a."""
        if not self._has_sel():
            return
        del self._tokens[self._sel_a:self._sel_b]
        self._cursor = self._sel_a
        self._clear_sel()

    # ── Mouse callbacks from ExprDisplay ──────────────────────────────────────
    def _on_display_click(self, gap, tok_idx, mx, slot_tok=None, slot_spec=None):
        """Called on mouse press (no drag).  gap = cursor gap position (0..len).
        slot_tok / slot_spec are set when click landed inside a nested slot."""
        self._clear_sel()

        if slot_tok is not None:
            # Click inside a FracToken or ExprToken slot — enter it
            # First deactivate any previously active token
            if self._active is not None:
                self._active.editing = False
                self._active = None
            # Mark all ancestors as editing so highlight propagates
            ancestor = self._find_parent(self._tokens, slot_tok)
            while ancestor is not None:
                ancestor.editing = True
                ancestor = self._find_parent(self._tokens, ancestor)
            # Activate the clicked token and move cursor to end of clicked slot
            slot_tok.editing = True
            self._active = slot_tok
            if isinstance(slot_tok, FracToken):
                slot_tok.part = slot_spec  # "num" or "den"
                sl = slot_tok.num if slot_spec == "num" else slot_tok.den
                slot_tok.cursor = len(sl)
            elif isinstance(slot_tok, ExprToken):
                slot_tok.slot_idx = slot_spec  # int
                slot_tok.cursor = len(slot_tok.slots[slot_spec])
        else:
            # Click outside any slot — exit to top-level
            if self._active is not None:
                self._active.editing = False
                self._active = None
            self._cursor = gap
        self._refresh()

    # ── Refresh ────────────────────────────────────────────────────────────────
    def _refresh(self):
        self.expr_disp.set_tokens(
            self._tokens, self._cursor,
            editing_token=self._active,
            sel_a=self._sel_a if self._active is None else None,
            sel_b=self._sel_b if self._active is None else None,
        )

    # ── Token evaluation strings ───────────────────────────────────────────────
    def _tokens_to_str(self):
        return tokens_to_eval_str(self._tokens)

    def _tokens_to_display_str(self):
        return tokens_to_display_str(self._tokens)

    # ── Navigation: Left ───────────────────────────────────────────────────────
    def _cur_left(self):
        self._clear_sel()
        at = self._active
        if at is not None:
            if isinstance(at, FracToken):
                if at.part == "den":
                    if at.cursor > 0:
                        at.cursor -= 1; self._refresh()
                    else:
                        # switch to numerator end
                        at.part = "num"; at.cursor = len(at.num); self._refresh()
                else:  # num
                    if at.cursor > 0:
                        # try to enter a nested token to the left
                        slot = at.num
                        if at.cursor > 0 and isinstance(slot[at.cursor - 1], (FracToken, ExprToken)):
                            inner = slot[at.cursor - 1]
                            # push context — not implemented deeply; just move cursor
                            at.cursor -= 1; self._refresh()
                        else:
                            at.cursor -= 1; self._refresh()
                    else:
                        self._exit_token(to_right=False)
                        self._refresh()
            elif isinstance(at, ExprToken):
                if at.cursor > 0:
                    at.cursor -= 1; self._refresh()
                elif at.slot_idx > 0:
                    at.slot_idx -= 1
                    at.cursor = len(at.slots[at.slot_idx]); self._refresh()
                else:
                    self._exit_token(to_right=False)
                    self._refresh()
        else:
            if self._cursor > 0:
                left_tok = self._tokens[self._cursor - 1]
                if isinstance(left_tok, (FracToken, ExprToken)):
                    self._enter_token(left_tok, from_right=True)
                    self._refresh()
                else:
                    self._cursor -= 1; self._refresh()

    # ── Navigation: Right ──────────────────────────────────────────────────────
    def _cur_right(self):
        self._clear_sel()
        at = self._active
        if at is not None:
            if isinstance(at, FracToken):
                if at.part == "num":
                    if at.cursor < len(at.num):
                        at.cursor += 1; self._refresh()
                    else:
                        at.part = "den"; at.cursor = 0; self._refresh()
                else:  # den
                    if at.cursor < len(at.den):
                        at.cursor += 1; self._refresh()
                    else:
                        self._exit_token(to_right=True)
                        self._refresh()
            elif isinstance(at, ExprToken):
                cur_slot = at.slots[at.slot_idx]
                if at.cursor < len(cur_slot):
                    at.cursor += 1; self._refresh()
                elif at.two_slots and at.slot_idx == 0:
                    at.slot_idx = 1; at.cursor = 0; self._refresh()
                else:
                    self._exit_token(to_right=True)
                    self._refresh()
        else:
            if self._cursor < len(self._tokens):
                right_tok = self._tokens[self._cursor]
                if isinstance(right_tok, (FracToken, ExprToken)):
                    self._enter_token(right_tok, from_right=False)
                    self._refresh()
                else:
                    self._cursor += 1; self._refresh()

    def _arrow_up(self):
        """
        Vertical navigation upward:
        - Outside any token: if cursor is next to a FracToken/ExprToken,
          enter it and land in its top slot (num / slot[0]).
        - Inside FracToken in den: switch to num.
        - Inside FracToken in num: try nested token at cursor; else exit upward.
        - Inside ExprToken at slot > 0: switch to slot 0.
        - Inside ExprToken at slot 0: try nested token at cursor; else exit upward.
        """
        self._clear_sel()
        at = self._active

        if at is None:
            tok = self._adjacent_vertical_token()
            if tok is not None:
                self._enter_vertical(tok, go_top=True)
                self._refresh()
            return

        if isinstance(at, FracToken):
            if at.part == "den":
                at.part = "num"
                at.cursor = len(at.num)
                self._refresh()
            else:
                # Already in num — try nested token, else exit to parent
                nested = self._nested_at_cursor(at.num, at.cursor)
                if nested is not None:
                    self._enter_vertical_nested(at, nested, go_top=True)
                    self._refresh()
                else:
                    self._exit_token(to_right=False)
                    self._refresh()

        elif isinstance(at, ExprToken):
            if at.slot_idx > 0:
                at.slot_idx = 0
                at.cursor = len(at.slots[0])
                self._refresh()
            else:
                # Already in slot 0 — try nested token, else exit to parent
                nested = self._nested_at_cursor(at.slots[at.slot_idx], at.cursor)
                if nested is not None:
                    self._enter_vertical_nested(at, nested, go_top=True)
                    self._refresh()
                else:
                    self._exit_token(to_right=False)
                    self._refresh()

    def _arrow_down(self):
        """
        Vertical navigation downward:
        - Outside any token: enter adjacent FracToken/ExprToken into its
          bottom slot (den / last slot).
        - Inside FracToken in num: switch to den.
        - Inside FracToken in den: try nested token, else exit upward.
        - Inside ExprToken with two_slots at slot 0: switch to slot 1.
        - Inside ExprToken at last slot: try nested FracToken/ExprToken at
          cursor position into its bottom slot; if none, exit upward.
        - Inside ExprToken with one slot (e.g. sin): look for FracToken/ExprToken
          adjacent to cursor in the slot and enter its bottom.
        """
        self._clear_sel()
        at = self._active

        if at is None:
            tok = self._adjacent_vertical_token()
            if tok is not None:
                self._enter_vertical(tok, go_top=False)
                self._refresh()
            return

        if isinstance(at, FracToken):
            if at.part == "num":
                at.part = "den"
                at.cursor = len(at.den)
                self._refresh()
            else:
                # Already in den — try nested token, else exit to parent
                nested = self._nested_at_cursor(at.den, at.cursor)
                if nested is not None:
                    self._enter_vertical_nested(at, nested, go_top=False)
                    self._refresh()
                else:
                    self._exit_token(to_right=True)
                    self._refresh()

        elif isinstance(at, ExprToken):
            last_slot = (1 if at.two_slots else 0)
            if at.slot_idx < last_slot:
                at.slot_idx = last_slot
                at.cursor = len(at.slots[last_slot])
                self._refresh()
            else:
                # At the bottommost slot — check for nested FracToken/ExprToken
                nested = self._nested_at_cursor(at.slots[at.slot_idx], at.cursor)
                if nested is not None:
                    self._enter_vertical_nested(at, nested, go_top=False)
                    self._refresh()
                else:
                    # Exit upward to parent context
                    self._exit_token(to_right=True)
                    self._refresh()

    # ── Vertical navigation helpers ───────────────────────────────────────────

    def _adjacent_vertical_token(self):
        """Return the FracToken/ExprToken immediately left or right of the
        top-level cursor, preferring left."""
        toks = self._tokens
        c = self._cursor
        # prefer token to the left of cursor
        if c > 0 and isinstance(toks[c - 1], (FracToken, ExprToken)):
            return toks[c - 1]
        # then token to the right
        if c < len(toks) and isinstance(toks[c], (FracToken, ExprToken)):
            return toks[c]
        return None

    def _enter_vertical(self, tok, go_top):
        """Enter tok from the outside, landing in its top slot (go_top=True)
        or bottom slot (go_top=False).  Sets _active and tok.editing."""
        tok.editing = True
        self._active = tok
        if isinstance(tok, FracToken):
            tok.part = "num" if go_top else "den"
            tok.cursor = len(tok.num) if go_top else len(tok.den)
        elif isinstance(tok, ExprToken):
            if go_top:
                tok.slot_idx = 0
                tok.cursor = len(tok.slots[0])
            else:
                tok.slot_idx = 1 if tok.two_slots else 0
                tok.cursor = len(tok.slots[tok.slot_idx])
        # Mark all ancestors as editing=True
        ancestor = self._find_parent(self._tokens, tok)
        while ancestor is not None:
            ancestor.editing = True
            ancestor = self._find_parent(self._tokens, ancestor)

    def _nested_at_cursor(self, slot, cursor):
        """Return the FracToken/ExprToken in slot[] that the cursor is
        immediately to the left of (position cursor-1) or right of (position
        cursor), preferring left.  Returns None if no nested token found."""
        if cursor > 0 and isinstance(slot[cursor - 1], (FracToken, ExprToken)):
            return slot[cursor - 1]
        if cursor < len(slot) and isinstance(slot[cursor], (FracToken, ExprToken)):
            return slot[cursor]
        return None

    def _enter_vertical_nested(self, parent, child, go_top):
        """Switch _active from parent to child (a nested token inside
        parent's current slot), entering child's top or bottom slot."""
        child.editing = True
        self._active = child
        if isinstance(child, FracToken):
            child.part = "num" if go_top else "den"
            child.cursor = len(child.num) if go_top else len(child.den)
        elif isinstance(child, ExprToken):
            if go_top:
                child.slot_idx = 0
                child.cursor = len(child.slots[0])
            else:
                child.slot_idx = 1 if child.two_slots else 0
                child.cursor = len(child.slots[child.slot_idx])


    # ── Insert: text token ────────────────────────────────────────────────────
    def _ins(self, tok_str):
        """Insert a string token.  If there is a selection, replace it."""
        # If text typed with selection → delete selection first
        if self._has_sel() and self._active is None:
            self._delete_sel()

        at = self._active
        if at is not None:
            if isinstance(at, FracToken):
                slot = at.num if at.part == "num" else at.den
                slot.insert(at.cursor, tok_str)
                at.cursor += 1
                self._refresh()
            elif isinstance(at, ExprToken):
                slot = at.slots[at.slot_idx]
                slot.insert(at.cursor, tok_str)
                at.cursor += 1
                self._refresh()
            return

        self._tokens.insert(self._cursor, tok_str)
        self._cursor += 1
        self._refresh()

    def _top_index(self, tok):
        for i, t in enumerate(self._tokens):
            if t is tok:
                return i
        return None

    # ── Insert: ExprToken ─────────────────────────────────────────────────────
    def _ins_expr(self, kind):
        """Insert a new ExprToken.

        Priority order:
        1. If there is a top-level selection → wrap it into the main slot.
        2. Inside a nested slot: check LEFT of cursor first (FracToken /
           ExprToken / parenthesised group), then RIGHT (number/token).
        3. Top-level, no selection: same left-then-right priority.

        Slot routing:
        - Most functions (sin, cos, sqrt, pow2, …): main slot = slots[0].
        - loga / xroot: main argument = slots[1]; slots[0] is the small
          subscript/superscript that the user fills in manually.
          Absorbed operand goes to slots[1]; cursor starts in slots[0].
        - pown: slots[0]=base (absorb here), slots[1]=exponent (fill manually).
        """
        # Which slot receives the absorbed operand, and where does the cursor
        # land after insertion?
        # arg_slot  : index of the slot that receives the operand
        # edit_slot : slot_idx the token starts editing in (where cursor lands)
        if kind in ("loga", "xroot"):
            arg_slot  = 1   # operand → main argument slot
            edit_slot = 0   # cursor starts in the small subscript/index slot
        else:
            arg_slot  = 0
            edit_slot = 0

        def _make_et(operand):
            """Build an ExprToken with `operand` in arg_slot, ready to edit."""
            et = ExprToken(kind)
            et.editing  = True
            et.slot_idx = edit_slot
            if operand:
                et.slots[arg_slot] = operand
            et.cursor = 0   # start at beginning of edit_slot (always empty)
            return et

        # ── Case 1: selection exists at top-level — wrap it ──────────────────
        if self._has_sel() and self._active is None:
            selected  = self._sel_tokens()
            insert_at = self._sel_a
            self._delete_sel()
            et = _make_et(selected)
            self._tokens.insert(insert_at, et)
            self._cursor = insert_at + 1
            self._active = et
            self._refresh()
            return

        # ── Case 2: inside a nested slot ─────────────────────────────────────
        at = self._active
        if at is not None:
            if isinstance(at, FracToken):
                slot = at.num if at.part == "num" else at.den
                left_op, left_start = self._collect_left_operand(slot, at.cursor)
                if left_op:
                    del slot[left_start:at.cursor]
                    at.cursor = left_start
                    et = _make_et(left_op)
                    slot.insert(at.cursor, et)
                    at.cursor += 1
                    at.editing = True
                    self._active = et
                    self._refresh()
                    return
                operand = self._collect_right_operand(slot, at.cursor)
                et = _make_et(operand)
                if operand:
                    del slot[at.cursor:at.cursor + len(operand)]
                slot.insert(at.cursor, et)
                at.cursor += 1
                at.editing = True
                self._active = et
                self._refresh()
                return
            elif isinstance(at, ExprToken):
                slot = at.slots[at.slot_idx]
                left_op, left_start = self._collect_left_operand(slot, at.cursor)
                if left_op:
                    del slot[left_start:at.cursor]
                    at.cursor = left_start
                    et = _make_et(left_op)
                    slot.insert(at.cursor, et)
                    at.cursor += 1
                    at.editing = True
                    self._active = et
                    self._refresh()
                    return
                operand = self._collect_right_operand(slot, at.cursor)
                et = _make_et(operand)
                if operand:
                    del slot[at.cursor:at.cursor + len(operand)]
                slot.insert(at.cursor, et)
                at.cursor += 1
                at.editing = True
                self._active = et
                self._refresh()
                return

        # ── Case 3: top-level, no selection ──────────────────────────────────
        left_op, left_start = self._collect_left_operand(self._tokens, self._cursor)
        if left_op:
            del self._tokens[left_start:self._cursor]
            self._cursor = left_start
            et = _make_et(left_op)
            self._tokens.insert(self._cursor, et)
            self._cursor += 1
            self._active = et
            self._refresh()
            return
        operand = self._collect_right_operand(self._tokens, self._cursor)
        et = _make_et(operand)
        if operand:
            del self._tokens[self._cursor:self._cursor + len(operand)]
        self._tokens.insert(self._cursor, et)
        self._cursor += 1
        self._active = et
        self._refresh()

    # ── Insert: FracToken ─────────────────────────────────────────────────────
    def _frac_new(self):
        """Insert a new FracToken.

        Priority order:
        1. If there is a top-level selection → selection becomes numerator.
        2. Inside a nested slot / top-level: check LEFT of cursor first
           (FracToken / ExprToken / closing-paren group), then RIGHT.
        """
        # ── Case 1: selection exists — wrap into numerator ────────────────────
        if self._has_sel() and self._active is None:
            selected  = self._sel_tokens()
            insert_at = self._sel_a
            self._delete_sel()
            ft = FracToken()
            ft.num    = selected
            ft.editing = True
            ft.part   = "den"           # enter denominator (numerator is filled)
            ft.cursor = 0
            self._tokens.insert(insert_at, ft)
            self._cursor = insert_at + 1
            self._active = ft
            self._refresh()
            return

        # ── Case 2: no selection ──────────────────────────────────────────────
        at = self._active
        ft = FracToken()
        ft.editing = True

        if at is None:
            # Try left first, then right
            left_op, left_start = self._collect_left_operand(self._tokens, self._cursor)
            if left_op:
                del self._tokens[left_start:self._cursor]
                self._cursor = left_start
                ft.num = left_op
                ft.part = "den"
                ft.cursor = 0
            else:
                operand = self._collect_right_operand(self._tokens, self._cursor)
                if operand:
                    del self._tokens[self._cursor:self._cursor + len(operand)]
                    ft.num = operand
                    ft.part = "den"
                    ft.cursor = 0
                else:
                    ft.part = "num"
                    ft.cursor = 0
            self._tokens.insert(self._cursor, ft)
            self._cursor += 1
            self._active = ft
            self._refresh()
            return

        if isinstance(at, FracToken):
            slot = at.num if at.part == "num" else at.den
            left_op, left_start = self._collect_left_operand(slot, at.cursor)
            if left_op:
                del slot[left_start:at.cursor]
                at.cursor = left_start
                ft.num = left_op
                ft.part = "den"
                ft.cursor = 0
            else:
                operand = self._collect_right_operand(slot, at.cursor)
                if operand:
                    del slot[at.cursor:at.cursor + len(operand)]
                    ft.num = operand
                    ft.part = "den"
                    ft.cursor = 0
                else:
                    ft.part = "num"
                    ft.cursor = 0
            slot.insert(at.cursor, ft)
            at.cursor += 1
            at.editing = True
        elif isinstance(at, ExprToken):
            slot = at.slots[at.slot_idx]
            left_op, left_start = self._collect_left_operand(slot, at.cursor)
            if left_op:
                del slot[left_start:at.cursor]
                at.cursor = left_start
                ft.num = left_op
                ft.part = "den"
                ft.cursor = 0
            else:
                operand = self._collect_right_operand(slot, at.cursor)
                if operand:
                    del slot[at.cursor:at.cursor + len(operand)]
                    ft.num = operand
                    ft.part = "den"
                    ft.cursor = 0
                else:
                    ft.part = "num"
                    ft.cursor = 0
            slot.insert(at.cursor, ft)
            at.cursor += 1
            at.editing = True

        self._active = ft
        self._refresh()

    # ── Backspace ─────────────────────────────────────────────────────────────
    def _back(self):
        # If there is a selection, delete it
        if self._has_sel() and self._active is None:
            self._delete_sel()
            self._refresh()
            return

        at = self._active
        if isinstance(at, FracToken):
            slot = at.num if at.part == "num" else at.den
            if at.cursor > 0:
                del slot[at.cursor - 1]
                at.cursor -= 1; self._refresh()
            elif at.part == "den":
                at.part = "num"; at.cursor = len(at.num); self._refresh()
            else:
                # At start of num — delete whole FracToken (from top or parent slot)
                at.editing = False
                self._active = None
                self._remove_token(at)
                self._refresh()
            return
        if isinstance(at, ExprToken):
            slot = at.slots[at.slot_idx]
            if at.cursor > 0:
                del slot[at.cursor - 1]
                at.cursor -= 1; self._refresh()
            elif at.slot_idx > 0:
                at.slot_idx -= 1
                at.cursor = len(at.slots[at.slot_idx]); self._refresh()
            else:
                at.editing = False
                self._active = None
                self._remove_token(at)
                self._refresh()
            return

        if self._cursor == 0:
            return
        self._cursor -= 1
        del self._tokens[self._cursor]
        self._refresh()

    def _remove_token(self, tok):
        """Remove tok from wherever it lives (top-level or nested slot)."""
        # Try top-level
        idx = self._top_index(tok)
        if idx is not None:
            del self._tokens[idx]
            self._cursor = idx
            return
        # Find in nested slot
        parent = self._find_parent(self._tokens, tok)
        if parent is not None:
            if isinstance(parent, FracToken):
                for slot in (parent.num, parent.den):
                    for i, t in enumerate(slot):
                        if t is tok:
                            del slot[i]
                            parent.cursor = i
                            self._active = parent
                            return
            elif isinstance(parent, ExprToken):
                for slot in parent.slots:
                    for i, t in enumerate(slot):
                        if t is tok:
                            del slot[i]
                            parent.cursor = i
                            self._active = parent
                            return

    def _clear(self):
        self._tokens = []
        self._cursor = 0
        self._active = None
        self._clear_sel()
        self.res_lbl.config(text="")
        self._res_frac_hide()
        self._refresh()

    def _toggle_angle(self):
        self.deg_mode = not self.deg_mode
        lbl = "Deg" if self.deg_mode else "Rad"
        self.mode_lbl.config(text=lbl)
        if self._deg_btn:
            self._deg_btn.config(text=lbl)

    def _mem_recall(self):
        self._ins(str(self.memory))

    def _hist(self, d):
        pass

    def _on_key(self, ev):
        k   = ev.char
        key = ev.keysym
        at = self._active
        if at is not None:
            if k in "0123456789.":
                self._ins(k)
            elif k in "+-*/()%":
                self._ins(k)
            elif key == "slash":
                if isinstance(at, FracToken):
                    at.part = "den"; at.cursor = 0; self._refresh()
                elif isinstance(at, ExprToken) and at.two_slots:
                    at.slot_idx = 1; at.cursor = 0; self._refresh()
            elif key == "Tab":
                if isinstance(at, FracToken):
                    at.part = "den"; at.cursor = 0; self._refresh()
                elif isinstance(at, ExprToken) and at.two_slots:
                    at.slot_idx = 1; at.cursor = 0; self._refresh()
            # strzałki obsługiwane przez osobne bindingi — nie blokuj
            return "break"
        if k in "0123456789.+-*/()%":
            self._ins(k)
        elif k == "^":
            self._ins_expr("pown")
        return "break"

    # ── Result ────────────────────────────────────────────────────────────────
    def _res_frac_show(self, f):
        if self._res_frac_cv is None:
            self._res_frac_cv = _SmallFracCanvas(self.res_lbl.master)
        self._res_frac_cv.draw(f.numerator, f.denominator)
        if not self._res_frac_vis:
            self._res_frac_cv.pack(anchor="e", padx=15)
            self._res_frac_vis = True

    def _res_frac_hide(self):
        if self._res_frac_cv and self._res_frac_vis:
            self._res_frac_cv.pack_forget()
            self._res_frac_cv.clear()
            self._res_frac_vis = False

    def _calc(self):
        raw = self._tokens_to_str().strip()
        if not raw:
            return

        env  = _make_env(self.deg_mode)
        safe = _normalize(raw)
        try:
            result = eval(safe, {"__builtins__": {}}, env)
        except ZeroDivisionError:
            self.res_lbl.config(text="Błąd: ÷ 0"); return
        except OverflowError:
            self.res_lbl.config(text="Przepełnienie"); return
        except Exception:
            self.res_lbl.config(text="Błąd składni"); return

        self._res_frac_hide()
        disp_raw = self._tokens_to_display_str()

        if isinstance(result, int):
            res_txt = str(result); frac = None
        elif isinstance(result, float):
            if result == math.floor(result) and abs(result) < 1e15:
                res_txt = str(int(result)); frac = None
            else:
                frac = _to_frac(result)
                res_txt = ("≈ {:.10g}".format(result) if frac
                           else "{:.10g}".format(result))
        else:
            res_txt = str(result); frac = None

        self.res_lbl.config(text=disp_raw + "  =  " + res_txt)
        if frac is not None:
            self._res_frac_show(frac)


# ─── MAŁY CANVAS UŁAMKA WYNIKOWEGO ───────────────────────────────────────────
class _SmallFracCanvas(tk.Canvas):
    FONT = ("Consolas", 14, "bold")
    PAD  = 6

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=DISP_BG, highlightthickness=0, **kw)

    def _sz(self, text):
        lbl = tk.Label(self, text=text, font=self.FONT, bg=DISP_BG, padx=0, pady=0)
        lbl.update_idletasks()
        w, h = lbl.winfo_reqwidth(), lbl.winfo_reqheight()
        lbl.destroy()
        return w, h

    def draw(self, num, den):
        self.delete("all")
        ns, ds = str(num), str(den)
        nw, nh = self._sz(ns)
        dw, dh = self._sz(ds)
        lw = max(nw, dw) + self.PAD * 2
        tw = lw + 12
        th = nh + dh + 10
        self.config(width=tw, height=th)
        cx = tw // 2
        self.create_text(cx, nh//2+1, text=ns, fill=FG, font=self.FONT, anchor="center")
        yl = nh + 4
        self.create_line(cx - lw//2, yl, cx + lw//2, yl, fill=FG, width=2)
        self.create_text(cx, yl+3+dh//2, text=ds, fill=FG, font=self.FONT, anchor="center")

    def clear(self):
        self.delete("all")
        self.config(width=1, height=1)


# ─── START ────────────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    root.geometry("1100x700")
    root.minsize(960, 580)
    root.configure(bg="#000000")

    if root.tk.call('tk', 'windowingsystem') == 'win32':
        root.state('zoomed')
    else:
        try:
            root.attributes('-zoomed', True)
        except Exception:
            pass

    Calculator(root)
    root.mainloop()

if __name__ == "__main__":
    main()