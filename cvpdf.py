"""Premium CV renderer (ReportLab). Draws a two-column A4 CV with a dark sidebar,
gold accents, circular photo, skill bars, language rings and a QR portfolio card."""
import io
import math
import os

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

W, H = A4
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def _register_fonts():
    try:
        for name, fn in (("P-Reg", "Poppins-Regular.ttf"), ("P-Med", "Poppins-Medium.ttf"),
                         ("P-Bold", "Poppins-Bold.ttf"), ("P-It", "Poppins-Italic.ttf")):
            pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, fn)))
        return {"reg": "P-Reg", "med": "P-Med", "bold": "P-Bold", "it": "P-It"}
    except Exception:  # fonts missing -> safe fallback
        return {"reg": "Helvetica", "med": "Helvetica-Bold", "bold": "Helvetica-Bold", "it": "Helvetica-Oblique"}


F = _register_fonts()

# ---------------------------------------------------------------- palette
def hx(s):
    return HexColor(s)


NAVY_D, NAVY, NAVY_M, NAVY_L = hx("#050d24"), hx("#0a1a40"), hx("#0e2760"), hx("#13306e")
BLUE, BLUE_L, BLUE_D = hx("#1f6bff"), hx("#4a95ff"), hx("#0f3ab5")
GOLD, GOLD_L, GOLD_D = hx("#c9a14a"), hx("#f1d98c"), hx("#8f6a1c")
INK, TEXT, MUTED = hx("#0b1d4a"), hx("#2a3042"), hx("#6b7488")
PAPER, WHITE = hx("#f5f6fb"), hx("#ffffff")

SW = 205            # sidebar width
SX = 26             # sidebar inner left padding
MX = SW + 30        # main column x
MW = W - MX - 32    # main column width


def mix(c1, c2, t):
    return Color(c1.red + (c2.red - c1.red) * t, c1.green + (c2.green - c1.green) * t,
                 c1.blue + (c2.blue - c1.blue) * t)


def side_color_at(y):
    top, mid, bot = hx("#0d2a6b"), hx("#081b47"), hx("#040b20")
    t = max(0.0, min(1.0, (H - y) / H))
    return mix(top, mid, t * 2) if t < .5 else mix(mid, bot, (t - .5) * 2)


# ---------------------------------------------------------------- text utils
def sw_(s, font, size, cs=0.0):
    return pdfmetrics.stringWidth(s, font, size) + cs * len(s)


def wrap(text, font, size, width):
    out = []
    for para in str(text or "").split("\n"):
        line = ""
        for word in para.split():
            while sw_(word, font, size) > width:
                k = len(word)
                while k > 1 and sw_(word[:k], font, size) > width:
                    k -= 1
                if line:
                    out.append(line)
                    line = ""
                out.append(word[:k])
                word = word[k:]
            cand = (line + " " + word) if line else word
            if sw_(cand, font, size) <= width:
                line = cand
            else:
                out.append(line)
                line = word
        if line:
            out.append(line)
    return out or [""]


def fit(text, font, size, maxw):
    if sw_(text, font, size) <= maxw:
        return text
    while text and sw_(text + "...", font, size) > maxw:
        text = text[:-1]
    return text + "..."


def txt(c, x, y, s, font, size, color, cs=0.0, align="l"):
    w = sw_(s, font, size, cs)
    if align == "c":
        x -= w / 2
    elif align == "r":
        x -= w
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setCharSpace(cs)
    t.textOut(s)
    c.drawText(t)


def grad_text(c, x, y, s, font, size, colors, pos=None, cs=0.0):
    c.saveState()
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setCharSpace(cs)
    t.setTextRenderMode(7)
    t.textOut(s)
    c.drawText(t)
    c.linearGradient(x, y + size * .78, x, y - size * .06, colors, pos)
    c.restoreState()


# ---------------------------------------------------------------- shape utils
def grad_path(c, path, x0, y0, x1, y1, colors, pos=None):
    c.saveState()
    c.clipPath(path, stroke=0, fill=0)
    c.linearGradient(x0, y0, x1, y1, colors, pos)
    c.restoreState()


def poly(c, pts):
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return p


def rr(c, x, y, w, h, r):
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    return p


def circ(c, x, y, r):
    p = c.beginPath()
    p.circle(x, y, r)
    return p


def hex_path(c, cx, cy, r):
    pts = [(cx + r * math.cos(math.radians(90 + 60 * i)), cy + r * math.sin(math.radians(90 + 60 * i)))
           for i in range(6)]
    return poly(c, pts)


# ---------------------------------------------------------------- icons
def ic_user(c, x, y, r, fg, bg):
    c.setFillColor(fg)
    c.circle(x, y + .34 * r, .3 * r, stroke=0, fill=1)
    p = c.beginPath()
    p.moveTo(x - .6 * r, y - .5 * r)
    p.curveTo(x - .6 * r, y - .02 * r, x + .6 * r, y - .02 * r, x + .6 * r, y - .5 * r)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def ic_brief(c, x, y, r, fg, bg):
    c.setFillColor(fg)
    c.roundRect(x - .64 * r, y - .42 * r, 1.28 * r, .84 * r, .12 * r, stroke=0, fill=1)
    c.setStrokeColor(fg)
    c.setLineWidth(.17 * r)
    c.roundRect(x - .25 * r, y + .32 * r, .5 * r, .3 * r, .07 * r, stroke=1, fill=0)
    c.setStrokeColor(bg)
    c.setLineWidth(.09 * r)
    c.line(x - .64 * r, y + .0 * r, x + .64 * r, y + .0 * r)
    c.setFillColor(bg)
    c.rect(x - .08 * r, y - .1 * r, .16 * r, .2 * r, stroke=0, fill=1)


def ic_cap(c, x, y, r, fg, bg):
    c.setFillColor(fg)
    c.drawPath(poly(c, [(x - .72 * r, y + .12 * r), (x, y + .46 * r), (x + .72 * r, y + .12 * r), (x, y - .2 * r)]), stroke=0, fill=1)
    c.drawPath(poly(c, [(x - .4 * r, y - .02 * r), (x, y - .2 * r), (x + .4 * r, y - .02 * r),
                        (x + .4 * r, y - .34 * r), (x, y - .52 * r), (x - .4 * r, y - .34 * r)]), stroke=0, fill=1)
    c.setStrokeColor(fg)
    c.setLineWidth(.1 * r)
    c.line(x + .66 * r, y + .12 * r, x + .66 * r, y - .3 * r)


def ic_chat(c, x, y, r, fg, bg):
    c.setFillColor(fg)
    c.roundRect(x - .66 * r, y - .12 * r, 1.32 * r, .78 * r, .2 * r, stroke=0, fill=1)
    c.drawPath(poly(c, [(x - .3 * r, y - .12 * r), (x - .46 * r, y - .52 * r), (x + .06 * r, y - .12 * r)]), stroke=0, fill=1)
    c.setFillColor(bg)
    for dx in (-.3, 0, .3):
        c.circle(x + dx * r, y + .27 * r, .08 * r, stroke=0, fill=1)


def ic_star(c, x, y, r, fg, bg):
    pts = []
    for i in range(10):
        rad = .7 * r if i % 2 == 0 else .3 * r
        a = math.radians(90 + 36 * i)
        pts.append((x + rad * math.cos(a), y + rad * math.sin(a)))
    c.setFillColor(fg)
    c.drawPath(poly(c, pts), stroke=0, fill=1)


def ic_code(c, x, y, r, fg, bg):
    c.setStrokeColor(fg)
    c.setLineWidth(.14 * r)
    c.setLineCap(1)
    c.setLineJoin(1)
    p = c.beginPath()
    p.moveTo(x - .22 * r, y + .42 * r); p.lineTo(x - .62 * r, y); p.lineTo(x - .22 * r, y - .42 * r)
    c.drawPath(p, stroke=1, fill=0)
    p = c.beginPath()
    p.moveTo(x + .22 * r, y + .42 * r); p.lineTo(x + .62 * r, y); p.lineTo(x + .22 * r, y - .42 * r)
    c.drawPath(p, stroke=1, fill=0)
    c.line(x + .1 * r, y + .5 * r, x - .1 * r, y - .5 * r)


def ic_grid(c, x, y, r, fg, bg):
    c.setFillColor(fg)
    for dx in (-.62, .06):
        for dy in (-.62, .06):
            c.roundRect(x + dx * r, y + dy * r, .56 * r, .56 * r, .1 * r, stroke=0, fill=1)


def ic_phone(c, x, y, r, fg, bg):
    c.setFillColor(fg)
    c.roundRect(x - .34 * r, y - .62 * r, .68 * r, 1.24 * r, .12 * r, stroke=0, fill=1)
    c.setFillColor(bg)
    c.rect(x - .22 * r, y - .38 * r, .44 * r, .8 * r, stroke=0, fill=1)
    c.circle(x, y - .5 * r, .07 * r, stroke=0, fill=1)


def ic_mail(c, x, y, r, fg, bg):
    c.setFillColor(fg)
    c.roundRect(x - .66 * r, y - .42 * r, 1.32 * r, .84 * r, .1 * r, stroke=0, fill=1)
    c.setStrokeColor(bg)
    c.setLineWidth(.1 * r)
    p = c.beginPath()
    p.moveTo(x - .62 * r, y + .34 * r); p.lineTo(x, y - .08 * r); p.lineTo(x + .62 * r, y + .34 * r)
    c.drawPath(p, stroke=1, fill=0)


def ic_pin(c, x, y, r, fg, bg):
    c.setFillColor(fg)
    c.circle(x, y + .2 * r, .42 * r, stroke=0, fill=1)
    c.drawPath(poly(c, [(x - .36 * r, y + .02 * r), (x + .36 * r, y + .02 * r), (x, y - .62 * r)]), stroke=0, fill=1)
    c.setFillColor(bg)
    c.circle(x, y + .2 * r, .16 * r, stroke=0, fill=1)


def ic_globe(c, x, y, r, fg, bg):
    c.setStrokeColor(fg)
    c.setLineWidth(.11 * r)
    c.circle(x, y, .64 * r, stroke=1, fill=0)
    c.ellipse(x - .27 * r, y - .64 * r, x + .27 * r, y + .64 * r, stroke=1, fill=0)
    c.line(x - .64 * r, y, x + .64 * r, y)
    dx = math.sqrt(.64 ** 2 - .32 ** 2) * r
    c.line(x - dx, y + .32 * r, x + dx, y + .32 * r)
    c.line(x - dx, y - .32 * r, x + dx, y - .32 * r)


ICONS = {"user": ic_user, "brief": ic_brief, "cap": ic_cap, "chat": ic_chat, "star": ic_star,
         "code": ic_code, "grid": ic_grid, "phone": ic_phone, "mail": ic_mail, "pin": ic_pin,
         "globe": ic_globe}


def hex_badge(c, cx, cy, r, icon, edge=GOLD_L):
    p = hex_path(c, cx, cy, r)
    grad_path(c, p, cx - r, cy + r, cx + r, cy - r, [BLUE, NAVY_L, NAVY])
    c.setStrokeColor(edge)
    c.setLineWidth(1)
    c.drawPath(p, stroke=1, fill=0)
    ICONS[icon](c, cx, cy, r * .56, WHITE, NAVY_L)


def dot_icon(c, cx, cy, r, icon=None, letters=None):
    p = circ(c, cx, cy, r)
    grad_path(c, p, cx - r, cy + r, cx + r, cy - r, [BLUE_L, BLUE_D])
    c.setStrokeColor(WHITE)
    c.setStrokeAlpha(.55)
    c.setLineWidth(.7)
    c.drawPath(p, stroke=1, fill=0)
    c.setStrokeAlpha(1)
    if icon:
        ICONS[icon](c, cx, cy, r * .6, WHITE, BLUE_D)
    elif letters:
        txt(c, cx, cy - 2.4, letters, F["bold"], 6.6, WHITE, align="c")


def check_bullet(c, cx, cy):
    c.setFillColor(NAVY_L)
    c.circle(cx, cy, 4.3, stroke=0, fill=1)
    c.setStrokeColor(WHITE)
    c.setLineWidth(1.1)
    c.setLineCap(1)
    c.setLineJoin(1)
    p = c.beginPath()
    p.moveTo(cx - 2, cy - .1); p.lineTo(cx - .6, cy - 1.6); p.lineTo(cx + 2.2, cy + 1.6)
    c.drawPath(p, stroke=1, fill=0)


def crown(c, cx, cy):
    pts = [(cx - 19, cy - 11), (cx - 22, cy + 8), (cx - 10, cy - 1), (cx, cy + 13), (cx + 10, cy - 1),
           (cx + 22, cy + 8), (cx + 19, cy - 11)]
    p = poly(c, pts)
    grad_path(c, p, cx, cy + 14, cx, cy - 14, [GOLD_L, GOLD, GOLD_D], [0, .5, 1])
    grad_path(c, rr(c, cx - 19, cy - 16, 38, 5, 1.5), cx, cy - 11, cx, cy - 16, [GOLD, GOLD_D])
    for px, py in ((cx - 22, cy + 9), (cx, cy + 14), (cx + 22, cy + 9)):
        c.setFillColor(GOLD_L)
        c.circle(px, py, 2.2, stroke=0, fill=1)


# ---------------------------------------------------------------- flow engine
class Flow:
    def __init__(self, bottom, top_first, top_next):
        self.bottom, self.top_next = bottom, top_next
        self.y, self.page, self.ops = top_first, 0, {}

    def add(self, h, fn, keep=0, cont=None):
        if self.y - (h + keep) < self.bottom and self.y < self.top_next:
            self.page += 1
            self.y = self.top_next
            if cont:  # repeat the section heading on the new page
                self.ops.setdefault(self.page, []).append((cont[1], self.y))
                self.y -= cont[0]
        self.ops.setdefault(self.page, []).append((fn, self.y))
        self.y -= h


# ---------------------------------------------------------------- header
def header_layout(cv):
    parts = (cv.get("name") or "YOUR NAME").upper().split()
    if len(parts) == 1:
        l1, l2 = parts[0], ""
    else:
        l1, l2 = " ".join(parts[:-1]), parts[-1]
    avail = W - 32 - 92 - MX
    size = 40.0
    while size > 18 and max(sw_(l1, F["bold"], size), sw_(l2, F["bold"], size)) > avail:
        size -= 1
    y1 = H - 62
    y2 = y1 - size * 1.04 if l2 else None
    div_y = (y2 if l2 else y1) - 24
    return {"l1": l1, "l2": l2, "size": size, "y1": y1, "y2": y2, "div_y": div_y, "end": div_y - 24}


def draw_header(c, cv, lay):
    txt(c, MX, lay["y1"], lay["l1"], F["bold"], lay["size"], INK)
    if lay["l2"]:
        grad_text(c, MX, lay["y2"], lay["l2"], F["bold"], lay["size"], [GOLD_L, GOLD, GOLD_D], [0, .45, 1])
    y = lay["div_y"]
    c.setStrokeColor(BLUE_D)
    c.setLineWidth(1.2)
    c.line(MX, y, MX + 62, y)
    c.setFillColor(BLUE_D)
    c.circle(MX + 66, y, 2, stroke=0, fill=1)
    c.setLineWidth(.7)
    c.setDash(1, 2.4)
    c.setStrokeAlpha(.6)
    c.line(MX + 76, y, MX + MW - 100, y)
    c.setDash()
    c.setStrokeAlpha(1)

    # ribbon badge with crown + job title
    rw, rx = 80, W - 32 - 80
    pts = [(rx, H), (rx + rw, H), (rx + rw, H - 104), (rx + rw / 2, H - 128), (rx, H - 104)]
    shadow = poly(c, [(a + 2, b - 3) for a, b in pts])
    c.setFillColor(NAVY_D)
    c.setFillAlpha(.18)
    c.drawPath(shadow, stroke=0, fill=1)
    c.setFillAlpha(1)
    p = poly(c, pts)
    grad_path(c, p, rx, H, rx, H - 128, [NAVY_L, NAVY, NAVY_D])
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.3)
    ins = [(rx + 4, H), (rx + 4, H - 100), (rx + rw / 2, H - 121), (rx + rw - 4, H - 100), (rx + rw - 4, H)]
    q = c.beginPath()
    q.moveTo(*ins[0])
    for pt in ins[1:]:
        q.lineTo(*pt)
    c.drawPath(q, stroke=1, fill=0)
    crown(c, rx + rw / 2, H - 38)
    title = (cv.get("title") or "").upper()
    size = 8.6
    while size > 5.2:
        lines = wrap(title, F["med"], size, rw - 16)
        if len(lines) <= 3 and all(sw_(l, F["med"], size, .6) <= rw - 14 for l in lines):
            break
        size -= .4
    lines = wrap(title, F["med"], size, rw - 16)[:3]
    ty = H - 66
    for i, ln in enumerate(lines):
        txt(c, rx + rw / 2, ty - i * (size + 3.4), ln, F["med"], size, GOLD_L if i == 0 else WHITE, cs=.6, align="c")


# ---------------------------------------------------------------- page background
def draw_background(c, first, cv, photo_path):
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, stroke=0, fill=1)

    # bottom swooshes (left + right)
    for flip in (False, True):
        def X(v):
            return v if not flip else W - v
        gold = poly(c, [(X(0), 40), (X(0), 45), (X(212), 0), (X(204), 0)])
        grad_path(c, gold, 0, 0, W, 0, [GOLD_D, GOLD_L, GOLD_D])
        blue = poly(c, [(X(0), 0), (X(0), 40), (X(204), 0)])
        grad_path(c, blue, X(0), 0, X(204), 0, [BLUE_D, BLUE_L])
        navy = poly(c, [(X(0), 0), (X(0), 26), (X(132), 0)])
        grad_path(c, navy, X(0), 0, X(132), 0, [NAVY_D, NAVY_L])

    # sidebar
    sb = poly(c, [(0, H), (SW, H), (SW, 94), (SW / 2, 42), (0, 94)])
    c.saveState()
    c.clipPath(sb, stroke=0, fill=0)
    c.linearGradient(0, H, 0, 0, [hx("#0d2a6b"), hx("#081b47"), hx("#040b20")], [0, .5, 1])
    if first:
        cy = H - 122
        c.radialGradient(SW / 2, cy, 120, [hx("#2a6bff"), hx("#1346b8"), side_color_at(cy - 100)], [0, .6, 1], extend=False)
    # diagonal light streak
    c.setFillColor(WHITE)
    c.setFillAlpha(.035)
    c.drawPath(poly(c, [(0, H - 360), (SW, H - 300), (SW, H - 420), (0, H - 480)]), stroke=0, fill=1)
    c.drawPath(poly(c, [(0, 330), (SW, 400), (SW, 440), (0, 370)]), stroke=0, fill=1)
    c.restoreState()

    c.setStrokeColor(GOLD)
    c.setStrokeAlpha(.55)
    c.setLineWidth(.8)
    ln = c.beginPath()
    ln.moveTo(10, H); ln.lineTo(10, 100); ln.lineTo(SW / 2, 54); ln.lineTo(SW - 10, 100); ln.lineTo(SW - 10, H)
    c.drawPath(ln, stroke=1, fill=0)
    c.setStrokeAlpha(1)

    # signature block at the sidebar tip
    nm = cv.get("name") or ""
    s = 15.0
    while s > 8 and sw_(nm, F["it"], s) > 140:
        s -= .5
    txt(c, SW / 2, 80, nm, F["it"], s, GOLD_L, align="c")
    title = (cv.get("title") or "").upper()
    t = 6.6
    while t > 4.5 and sw_(title, F["med"], t, 1.4) > 96:
        t -= .3
    txt(c, SW / 2, 66, title, F["med"], t, GOLD, cs=1.4, align="c")

    if first:
        cx, cy, R = SW / 2, H - 122, 72
        # gold ring
        grad_path(c, circ(c, cx, cy, R + 6), cx - R, cy + R, cx + R, cy - R, [GOLD_L, GOLD, GOLD_D, GOLD_L], [0, .35, .7, 1])
        c.setFillColor(NAVY_D)
        c.circle(cx, cy, R + 1.6, stroke=0, fill=1)
        c.saveState()
        c.clipPath(circ(c, cx, cy, R), stroke=0, fill=0)
        if photo_path and os.path.exists(photo_path):
            c.drawImage(ImageReader(photo_path), cx - R, cy - R, 2 * R, 2 * R)
        else:
            c.linearGradient(cx - R, cy + R, cx + R, cy - R, [NAVY_L, NAVY_D])
            ini = "".join(w[0] for w in (cv.get("name") or "?").split()[:2]).upper()
            txt(c, cx, cy - 16, ini, F["bold"], 46, GOLD_L, align="c")
        c.restoreState()

        # chevron band below the photo
        yA = H - 250
        band = poly(c, [(0, yA), (SW / 2, yA - 36), (SW, yA), (SW, yA - 22), (SW / 2, yA - 58), (0, yA - 22)])
        grad_path(c, band, 0, 0, SW, 0, [BLUE_D, BLUE_L, BLUE_D], [0, .5, 1])
        c.setStrokeColor(GOLD_L)
        c.setLineWidth(1.5)
        e = c.beginPath()
        e.moveTo(0, yA); e.lineTo(SW / 2, yA - 36); e.lineTo(SW, yA)
        c.drawPath(e, stroke=1, fill=0)
        c.setStrokeAlpha(.55)
        c.setLineWidth(.7)
        e = c.beginPath()
        e.moveTo(0, yA - 25); e.lineTo(SW / 2, yA - 61); e.lineTo(SW, yA - 25)
        c.drawPath(e, stroke=1, fill=0)
        c.setStrokeAlpha(1)


# ---------------------------------------------------------------- sidebar blocks
def side_heading(icon, text):
    def fn(c, y):
        hex_badge(c, SX + 14, y - 19, 15, icon)
        txt(c, SX + 38, y - 24, text.upper(), F["med"], 12, WHITE, cs=1)
        c.setStrokeColor(GOLD)
        c.setStrokeAlpha(.75)
        c.setLineWidth(.8)
        c.line(SX + 38, y - 31, SW - 18, y - 31)
        c.setStrokeAlpha(1)
    return 42, fn


def side_item(label, value, icon=None, letters=None, url=None):
    tx = SX + 30
    tw = SW - tx - 16
    fs = 8.3
    if " " not in value.strip():
        while fs > 6.4 and sw_(value, F["reg"], fs) > tw:
            fs -= .2
    lines = wrap(value, F["reg"], fs, tw)
    h = max(25, 9 + (9 if label else 0) + len(lines) * 11.2 + 4)

    def fn(c, y):
        dot_icon(c, SX + 10, y - 11, 10, icon, letters)
        base = y - 9
        if label:
            txt(c, tx, y - 8, label.upper(), F["med"], 6.4, GOLD_L, cs=.6)
            base = y - 18
        for i, ln in enumerate(lines):
            txt(c, tx, base - i * 11.2, ln, F["reg"], fs, WHITE)
        if url:
            c.linkURL(url, (tx, base - (len(lines) - 1) * 11.2 - 2, tx + tw, base + 8), relative=0, thickness=0)
    return h, fn


def skill_item(name, pct):
    def fn(c, y):
        right = SW - 18
        fs = 8.4
        while fs > 6.6 and sw_(name, F["med"], fs) > right - SX - 28:
            fs -= .2
        txt(c, SX, y - 9, fit(name, F["med"], fs, right - SX - 28), F["med"], fs, WHITE)
        txt(c, right, y - 9, "%d%%" % pct, F["reg"], 7.2, GOLD_L, align="r")
        bw = right - SX
        c.setFillColor(hx("#26365f"))
        c.roundRect(SX, y - 18.5, bw, 3.6, 1.8, stroke=0, fill=1)
        fw = max(4, bw * pct / 100.0)
        grad_path(c, rr(c, SX, y - 18.5, fw, 3.6, 1.8), SX, 0, SX + fw, 0, [BLUE_D, BLUE_L])
        c.setFillColor(GOLD_L)
        c.circle(SX + fw, y - 16.7, 2.3, stroke=0, fill=1)
    return 24, fn


SOCIAL_CODES = {"github": "GH", "linkedin": "in", "facebook": "f", "instagram": "Ig", "twitter / x": "X",
                "x": "X", "youtube": "Yt", "behance": "Be"}


# ---------------------------------------------------------------- main blocks
def main_heading(icon, text):
    def fn(c, y):
        hex_badge(c, MX + 16, y - 19, 15, icon)
        label = text.upper()
        txt(c, MX + 41, y - 24, label, F["bold"], 12.2, INK, cs=.8)
        x1 = MX + 41 + sw_(label, F["bold"], 12.2, .8) + 12
        x2 = MX + MW - 4
        if x2 > x1 + 10:
            c.setStrokeColor(BLUE_D)
            c.setStrokeAlpha(.5)
            c.setLineWidth(.8)
            c.line(x1, y - 19.5, x2, y - 19.5)
            c.setStrokeAlpha(1)
            c.setFillColor(BLUE_D)
            c.circle(x2, y - 19.5, 2, stroke=0, fill=1)
    return 42, fn


def summary_block(text):
    lines = wrap(text, F["reg"], 8.8, MW - 40)
    h = len(lines) * 13.6 + 30

    def fn(c, y):
        c.setFillColor(NAVY_D)
        c.setFillAlpha(.09)
        c.roundRect(MX + 2, y - h - 3, MW, h, 10, stroke=0, fill=1)
        c.setFillAlpha(1)
        grad_path(c, rr(c, MX, y - h, MW, h, 10), MX, y, MX + MW, y - h, [hx("#eceff7"), WHITE])
        c.setStrokeColor(hx("#d9deea"))
        c.setLineWidth(.6)
        c.roundRect(MX, y - h, MW, h, 10, stroke=1, fill=0)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.8)
        c.setLineCap(1)
        for sgn, yy in ((1, y), (-1, y - h)):
            p = c.beginPath()
            p.moveTo(MX + MW - 30, yy); p.lineTo(MX + MW - 6, yy)
            p.curveTo(MX + MW - 1.5, yy, MX + MW, yy - sgn * 1.5, MX + MW, yy - sgn * 6)
            p.lineTo(MX + MW, yy - sgn * 28)
            c.drawPath(p, stroke=1, fill=0)
        grad_path(c, rr(c, MX + MW - 3, y - h + 22, 3, h - 44, 1.5), 0, y, 0, y - h, [NAVY_L, NAVY_D])
        for i, ln in enumerate(lines):
            txt(c, MX + 18, y - 21 - i * 13.6, ln, F["reg"], 8.8, TEXT)
    return h + 14, fn


def exp_block(e):
    period = e.get("period") or ""
    pw = sw_(period, F["med"], 7.6) + 20 if period else 0
    role_lines = wrap((e.get("title") or "").upper(), F["bold"], 10, MW - (pw + 10 if pw else 0)) if e.get("title") else []
    company = e.get("company") or ""
    bl = [wrap(p, F["reg"], 8.5, MW - 20) for p in e.get("points", [])]
    h = len(role_lines) * 13 + (12 if company else 0) + 3 + sum(len(l) * 12 + 3 for l in bl) + 11

    def fn(c, y):
        cur = y
        if period:
            c.setFillColor(hx("#fffaf0"))
            c.setStrokeColor(GOLD)
            c.setLineWidth(.9)
            c.roundRect(MX + MW - pw, y - 15, pw, 17, 4, stroke=1, fill=1)
            txt(c, MX + MW - pw / 2, y - 9.2, period, F["med"], 7.6, GOLD_D, align="c")
        for ln in role_lines:
            txt(c, MX, cur - 10, ln, F["bold"], 10, INK)
            cur -= 13
        if company:
            txt(c, MX, cur - 8, company, F["med"], 8.8, GOLD_D)
            cur -= 12
        cur -= 3
        for lines in bl:
            check_bullet(c, MX + 5, cur - 8.5 + 2.9)
            for i, ln in enumerate(lines):
                txt(c, MX + 17, cur - 8.5 - i * 12, ln, F["reg"], 8.5, TEXT)
            cur -= len(lines) * 12 + 3
    return h, fn


def edu_block(e):
    school = wrap((e.get("school") or "").upper(), F["bold"], 10, MW) if e.get("school") else []
    degree = wrap(e.get("degree") or "", F["med"], 8.8, MW) if e.get("degree") else []
    meta = "   |   ".join(x for x in (e.get("period"), ("Grade: " + e["grade"]) if e.get("grade") else "") if x)
    h = len(school) * 13 + len(degree) * 12 + (12 if meta else 0) + 12

    def fn(c, y):
        cur = y
        for ln in school:
            txt(c, MX, cur - 10, ln, F["bold"], 10, INK)
            cur -= 13
        for ln in degree:
            txt(c, MX, cur - 9, ln, F["med"], 8.8, BLUE_D)
            cur -= 12
        if meta:
            txt(c, MX, cur - 9, meta, F["reg"], 8.2, MUTED)
    return h, fn


def project_block(p):
    name = wrap(p.get("name") or "", F["bold"], 10, MW)
    link = p.get("link_text") or ""
    bl = [wrap(t, F["reg"], 8.5, MW - 20) for t in p.get("points", [])]
    h = len(name) * 13 + (12 if link else 0) + 3 + sum(len(l) * 12 + 3 for l in bl) + 11

    def fn(c, y):
        cur = y
        for ln in name:
            txt(c, MX, cur - 10, ln, F["bold"], 10, INK)
            cur -= 13
        if link:
            lt = fit(link, F["med"], 8, MW)
            txt(c, MX, cur - 8, lt, F["med"], 8, BLUE)
            c.setStrokeColor(BLUE)
            c.setLineWidth(.4)
            c.line(MX, cur - 9.6, MX + sw_(lt, F["med"], 8), cur - 9.6)
            c.linkURL(p["link"], (MX, cur - 11, MX + sw_(lt, F["med"], 8), cur + 1), relative=0, thickness=0)
            cur -= 12
        cur -= 3
        for lines in bl:
            check_bullet(c, MX + 5, cur - 8.5 + 2.9)
            for i, ln in enumerate(lines):
                txt(c, MX + 17, cur - 8.5 - i * 12, ln, F["reg"], 8.5, TEXT)
            cur -= len(lines) * 12 + 3
    return h, fn


def cert_block(items):
    bl = [wrap(t, F["reg"], 8.6, MW - 20) for t in items]
    h = sum(len(l) * 12 + 4 for l in bl) + 8

    def fn(c, y):
        cur = y
        for lines in bl:
            c.setFillColor(GOLD)
            c.drawPath(poly(c, [(MX + 5, cur - 5), (MX + 9, cur - 8.5), (MX + 5, cur - 12), (MX + 1, cur - 8.5)]), stroke=0, fill=1)
            for i, ln in enumerate(lines):
                txt(c, MX + 17, cur - 9 - i * 12, ln, F["reg"], 8.6, TEXT)
            cur -= len(lines) * 12 + 4
    return h, fn


def lang_row(items):
    R = 22
    h = 8 + 2 * R + 34

    def fn(c, y):
        n = len(items)
        cell = MW / max(n, 3) if n < 4 else MW / 4.0
        start = MX + (MW - cell * n) / 2
        for i, it in enumerate(items):
            cx = start + cell * i + cell / 2
            cy = y - 8 - R
            c.setLineCap(1)
            c.setStrokeColor(hx("#dde2ee"))
            c.setLineWidth(5)
            c.circle(cx, cy, R, stroke=1, fill=0)
            c.setStrokeColor(BLUE)
            c.setLineWidth(5)
            ext = -min(359.9, 360.0 * it["pct"] / 100.0)
            c.arc(cx - R, cy - R, cx + R, cy + R, 90, ext)
            c.setStrokeColor(GOLD)
            c.setLineWidth(1.1)
            c.arc(cx - R - 5, cy - R - 5, cx + R + 5, cy + R + 5, 90, ext)
            txt(c, cx, cy - 3.6, "%d%%" % it["pct"], F["bold"], 10.2, INK, align="c")
            txt(c, cx, cy - R - 14, fit(it["name"].upper(), F["bold"], 7.8, cell - 6), F["bold"], 7.8, INK, cs=.5, align="c")
            txt(c, cx, cy - R - 24, it["level"], F["reg"], 7, MUTED, align="c")
    return h, fn


def portfolio_block(pf):
    h = 128

    def fn(c, y):
        c.setFillColor(NAVY_D)
        c.setFillAlpha(.12)
        c.roundRect(MX + 2, y - h - 3, MW, h, 12, stroke=0, fill=1)
        c.setFillAlpha(1)
        grad_path(c, rr(c, MX, y - h, MW, h, 12), MX, y, MX + MW, y - h, [NAVY_L, NAVY, NAVY_D])
        c.setStrokeColor(GOLD)
        c.setStrokeAlpha(.7)
        c.setLineWidth(.9)
        c.roundRect(MX + 3, y - h + 3, MW - 6, h - 6, 10, stroke=1, fill=0)
        c.setStrokeAlpha(1)
        # QR
        qx, qy, qs = MX + 16, y - 16 - 76, 76
        c.setFillColor(WHITE)
        c.roundRect(qx - 4, qy - 4, qs + 8, qs + 8, 6, stroke=0, fill=1)
        try:
            w = qr.QrCodeWidget(pf["url"])
            b = w.getBounds()
            bw, bh = b[2] - b[0], b[3] - b[1]
            d = Drawing(qs, qs, transform=[qs / bw, 0, 0, qs / bh, 0, 0])
            d.add(w)
            renderPDF.draw(d, c, qx, qy)
        except Exception:
            pass
        # divider + text
        tx = qx + qs + 20
        c.setStrokeColor(WHITE)
        c.setStrokeAlpha(.25)
        c.line(tx - 10, y - 18, tx - 10, y - 88)
        c.setStrokeAlpha(1)
        txt(c, tx, y - 32, "CHECK OUT MY WORK", F["bold"], 9, GOLD_L, cs=.4)
        for i, ln in enumerate(wrap("Scan the QR code or visit the link to explore my portfolio and projects.", F["reg"], 7.8, MW - (tx - MX) - 62)):
            txt(c, tx, y - 46 - i * 10.5, ln, F["reg"], 7.8, hx("#dfe6f7"))
        ic_globe(c, MX + MW - 40, y - 52, 30, GOLD, NAVY)
        # link pill
        px, pw_, py = MX + 16, MW - 32, y - h + 12
        grad_path(c, rr(c, px, py, pw_, 20, 10), px, 0, px + pw_, 0, [BLUE_D, BLUE, BLUE_D])
        label = fit(pf["text"], F["med"], 8.4, pw_ - 20)
        txt(c, px + pw_ / 2, py + 6.4, label, F["med"], 8.4, WHITE, align="c")
        c.linkURL(pf["url"], (px, py, px + pw_, py + 20), relative=0, thickness=0)
    return h + 6, fn


# ---------------------------------------------------------------- build
def build_pdf(cv, photo_path=None):
    lay = header_layout(cv)
    main = Flow(bottom=62, top_first=lay["end"], top_next=H - 46)
    side = Flow(bottom=116, top_first=H - 326, top_next=H - 46)

    def section(flow, icon, title, blocks, heading=main_heading):
        if not blocks:
            return
        hh, hf = heading(icon, title)
        first_h = blocks[0][0]
        flow.add(hh, hf, keep=first_h)
        for h, fn in blocks:
            flow.add(h, fn, cont=(hh, hf))

    # ---- main column
    if cv.get("summary"):
        section(main, "user", "Professional Summary", [summary_block(cv["summary"])])
    section(main, "brief", "Work Experience", [exp_block(e) for e in cv.get("experience", [])])
    section(main, "cap", "Education", [edu_block(e) for e in cv.get("education", [])])
    section(main, "code", "Projects", [project_block(p) for p in cv.get("projects", [])])
    if cv.get("certificates"):
        section(main, "star", "Certificates", [cert_block(cv["certificates"])])
    langs = cv.get("languages", [])
    if langs:
        per = 4 if len(langs) >= 4 else 3
        section(main, "chat", "Languages", [lang_row(langs[i:i + per]) for i in range(0, len(langs), per)])
    if cv.get("portfolio"):
        section(main, "globe", "Portfolio", [portfolio_block(cv["portfolio"])])

    # ---- sidebar
    contact = []
    if cv.get("phone"):
        contact.append(side_item("", cv["phone"], icon="phone"))
    if cv.get("email"):
        contact.append(side_item("", cv["email"], icon="mail", url="mailto:" + cv["email"]))
    if cv.get("portfolio"):
        contact.append(side_item("Portfolio", cv["portfolio"]["text"], icon="globe", url=cv["portfolio"]["url"]))
    if cv.get("address"):
        contact.append(side_item("", cv["address"], icon="pin"))
    section(side, "user", "Contact", contact, heading=side_heading)

    soc = []
    for s in cv.get("social", []):
        code = SOCIAL_CODES.get(s["label"].lower(), s["label"][:2].title())
        known = s["label"].lower() in SOCIAL_CODES
        soc.append(side_item("" if known else s["label"], s["text"], letters=code, url=s["url"]))
    section(side, "globe", "Social", soc, heading=side_heading)

    section(side, "grid", "Skills", [skill_item(s["name"], s["pct"]) for s in cv.get("skills", [])], heading=side_heading)

    # ---- render
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("%s - CV" % (cv.get("name") or "CV"))
    c.setAuthor(cv.get("name") or "")
    pages = max([main.page, side.page] + list(main.ops) + list(side.ops)) + 1
    for p in range(pages):
        draw_background(c, p == 0, cv, photo_path)
        if p == 0:
            draw_header(c, cv, lay)
        for fn, y in main.ops.get(p, []):
            fn(c, y)
        for fn, y in side.ops.get(p, []):
            fn(c, y)
        c.showPage()
    c.save()
    return buf.getvalue()
