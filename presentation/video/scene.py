"""Animate the intro using the narration timeline from tts.py.

Render from presentation/video:
  uv run --no-project --python 3.12 --with manim==0.19.0 --with "pillow<11" manim -qh --fps 30 -r 1920,1080 scene.py Intro
"""
import json
from pathlib import Path

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, UL, AnimationGroup, Axes, Circle, Create, Ellipse, FadeIn, FadeOut,
                   GrowFromCenter, ImageMobject, Indicate, Line, LaggedStart, Rectangle, RoundedRectangle, Scene, Square,
                   Text, Transform, ValueTracker, VGroup, VMobject, Write, always_redraw, config, linear, rate_functions, smooth)

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
TL = json.loads((HERE / "build" / "timeline.json").read_text())
SC = {s["id"]: s for s in TL["scenes"]}
CAPS = json.loads((HERE / "narration.json").read_text()).get("captions", {})

INK, INK2, LINE = "#1B1916", "#24211D", "#3A352F"
PAPER, MUTED, DIM = "#F6F2EA", "#A39A8D", "#6D665C"
BTC, SLATE, TEAL, BRICK, STEEL, SAGE, SAND = "#F7931A", "#2F4858", "#1F7A6D", "#B4432F", "#4C78A8", "#7A9A62", "#A8A196"
SERIF, SANS, MONO = "Caladea", "Inter", "JetBrains Mono"
config.background_color = INK

meta = json.loads((ROOT / "web/public/data/meta.json").read_text())
dec = json.loads((ROOT / "artifacts/decisions.json").read_text())
whom = json.loads((ROOT / "web/public/data/whomines.json").read_text())
timeline = json.loads((ROOT / "web/public/data/timeline.json").read_text())
BLOCKS = meta["counts"]["blocks"]
bitaxe = next(a for a in dec["advisor"] if a["device"].startswith("Bitaxe") and a["country"] == "Hong Kong" and a["tariff"] == "business")
ODDS = round(1 / bitaxe["solo_p_block_per_year"])
SOLO25 = int(whom["solo_by_year"]["2025"])


def T(s, size=36, color=PAPER, font=SANS, weight="NORMAL", **kw):
    return Text(s, font=font, font_size=size, color=color, weight=weight, **kw)


def wrap(s, n=64):
    out, line = [], ""
    for w in s.split():
        if len(line) + len(w) + 1 > n:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    return "\n".join(out + [line])


def logo(size=1.6):
    g = VGroup()
    g.add(RoundedRectangle(corner_radius=size * 0.2, width=size, height=size, fill_color=PAPER, fill_opacity=1, stroke_width=0))
    c = np.array([-size * 0.0625, size * 0.0417, 0])
    r = size * 13 / 48
    g.add(Circle(radius=r, stroke_color=INK, stroke_width=size * 3.2).move_to(c))
    g.add(Ellipse(width=r * 0.86, height=2 * r, stroke_color=INK, stroke_width=size * 2.6).move_to(c))
    g.add(Line(c + LEFT * r, c + RIGHT * r, stroke_color=INK, stroke_width=size * 2.6))
    sq = Square(side_length=size * 13 / 48, fill_color=BTC, fill_opacity=1, stroke_color=PAPER, stroke_width=size * 4)
    g.add(sq.move_to(np.array([size * (31.5 / 48 - 0.5), -size * (32.5 / 48 - 0.5), 0])))
    return g


def block(label, side=1.1, color=PAPER, fill=INK2, size=22):
    sq = Square(side_length=side, stroke_color=color, stroke_width=3, fill_color=fill, fill_opacity=1)
    return VGroup(sq, T(label, size, color, MONO).move_to(sq))


class Intro(Scene):
    # Timing and captions
    cap = None

    def now(self):
        return self.renderer.time

    def sync(self, t):
        d = t - self.now()
        if d > 1 / 30:
            self.wait(d)

    def say(self, line, *anims):
        """Show the next subtitle and start its animations with the narration."""
        self.sync(line["start"] - 0.2)
        txt = wrap(CAPS.get(line["text"], line["text"]))
        t = T(txt, 30, PAPER, SANS, line_spacing=0.9)
        bg = RoundedRectangle(corner_radius=0.08, width=t.width + 0.6, height=t.height + 0.34, fill_color="#0F0E0C",
                              fill_opacity=0.82, stroke_width=0)
        new = VGroup(bg, t).to_edge(DOWN, buff=0.32)
        if self.cap is not None:  # Remove the previous caption before showing the next.
            self.play(FadeOut(self.cap), run_time=0.15)
        a = [FadeIn(new, run_time=0.3)]
        self.cap = new
        self.play(*a, *anims)  # Keep each animation's run_time; wait for the longest.

    def clear_stage(self, keep=(), run_time=0.6):
        keep = set(keep)  # Clear captions when changing scenes too.
        mobs = [m for m in self.mobjects if m not in keep]
        self.cap = None
        # Cover images instead of fading them to avoid the renderer bug.
        imgs = [m for m in mobs if isinstance(m, ImageMobject)]
        covers = [Rectangle(width=m.width + 0.1, height=m.height + 0.1, fill_color=INK, fill_opacity=1, stroke_width=0).move_to(m) for m in imgs]
        anims = [FadeOut(m) for m in mobs if m not in imgs] + [FadeIn(c) for c in covers]
        if anims:
            self.play(*anims, run_time=run_time)
        self.remove(*imgs, *covers)

    def construct(self):
        bar = Rectangle(width=config.frame_width, height=0.06, fill_color=BTC, fill_opacity=1, stroke_width=0).to_edge(UP, buff=0)
        self.add(bar)
        self.genesis()
        self.hashrate()
        self.lottery()
        self.fingerprint()
        self.questions()
        self.title()

    def kicker(self, s):
        k = T(s, 22, BTC, MONO).to_corner(UL, buff=0.6).shift(DOWN * 0.15)
        self.play(FadeIn(k, shift=RIGHT * 0.2), run_time=0.5)
        return k

    def genesis(self):
        S = SC["genesis"]
        L = S["lines"]
        k = self.kicker("01 · GENESIS")
        date = T("03 · 01 · 2009", 40, MUTED, MONO).shift(UP * 1.9)
        b0 = block("#0", 1.5, BTC, INK2, 30)
        self.play(Write(date), run_time=1.2)
        self.play(GrowFromCenter(b0), run_time=0.9)
        self.say(L[0], Indicate(b0, color=BTC, scale_factor=1.08, run_time=1.4))
        # laptop → block → reward
        scr = RoundedRectangle(corner_radius=0.06, width=1.7, height=1.1, stroke_color=PAPER, stroke_width=3)
        base = VMobject(stroke_color=PAPER, stroke_width=3).set_points_as_corners([[-1.05, -0.62, 0], [1.05, -0.62, 0], [0.85, -0.78, 0], [-0.85, -0.78, 0], [-1.05, -0.62, 0]])
        laptop = VGroup(scr, base).shift(LEFT * 4.2)
        lap_t = T("one laptop", 24, MUTED).next_to(laptop, DOWN, buff=0.35)
        arrow1 = Line(LEFT * 3.0, LEFT * 1.0, stroke_color=DIM, stroke_width=3)
        reward = VGroup(T("50 BTC", 44, BTC, MONO, weight="BOLD"), T("block reward", 24, MUTED)).arrange(DOWN, buff=0.15).shift(RIGHT * 4.2)
        arrow2 = Line(RIGHT * 1.0, RIGHT * 3.0, stroke_color=DIM, stroke_width=3)
        self.say(L[1], LaggedStart(FadeIn(laptop, shift=RIGHT * 0.3), FadeIn(lap_t), Create(arrow1), lag_ratio=0.35, run_time=1.6))
        self.play(Create(arrow2), FadeIn(reward, shift=LEFT * 0.3), run_time=1.0)
        self.sync(L[1]["end"] + 0.3)
        # the chain starts to grow
        chain = VGroup(*[block(f"#{i}", 0.9, PAPER if i else BTC, INK2, 20) for i in range(1, 6)]).arrange(RIGHT, buff=0.45)
        self.play(FadeOut(VGroup(laptop, lap_t, arrow1, arrow2, reward, date)), b0.animate.scale(0.6).move_to(LEFT * 5.2), run_time=0.8)
        chain.next_to(b0, RIGHT, buff=0.45)
        links = VGroup(*[Line(a.get_right(), b.get_left(), stroke_color=DIM, stroke_width=3) for a, b in zip([b0, *chain[:-1]], chain)])
        self.play(LaggedStart(*[AnimationGroup(Create(l), FadeIn(c, shift=LEFT * 0.2)) for l, c in zip(links, chain)], lag_ratio=0.5, run_time=1.6))
        self.sync(S["end"] - 0.6)
        self.clear_stage(keep=[self.mobjects[0]], run_time=0.6)

    def hashrate(self):
        S = SC["hashrate"]
        L = S["lines"]
        k = self.kicker("02 · SEVENTEEN YEARS OF HASH POWER")
        pts = [(int(r["w"][:4]) + (int(r["w"][5:7]) - 1) / 12 + int(r["w"][8:10]) / 365, np.log10(r["h"] * 1e18)) for r in timeline if r["h"]]
        ax = Axes(x_range=[2009, 2027, 2], y_range=[3, 22, 3], x_length=11.0, y_length=4.3, tips=False,
                  axis_config={"stroke_color": DIM, "stroke_width": 2, "include_ticks": True, "tick_size": 0.05}).shift(UP * 0.35 + RIGHT * 0.5)
        xl = VGroup(*[T(str(y), 18, MUTED, MONO).next_to(ax.c2p(y, 3), DOWN, buff=0.15) for y in range(2010, 2027, 4)])
        yl = VGroup(*[T({6: "10⁶", 12: "10¹²", 18: "10¹⁸"}[v], 18, MUTED, MONO).next_to(ax.c2p(2009, v), LEFT, buff=0.15) for v in (6, 12, 18)])
        ylab = T("hashes per second (log scale)", 18, MUTED).next_to(ax, UP, buff=0.1).align_to(ax, LEFT)
        eras = [("CPU", 2009.0, 2010.55, SAND), ("GPU", 2010.55, 2011.42, STEEL), ("FPGA", 2011.42, 2013.08, SAGE),
                ("ASIC", 2013.08, 2016.42, SLATE), ("Industrial ASIC", 2016.42, 2026.9, BTC)]
        bands = VGroup(*[Rectangle(width=ax.c2p(b, 3)[0] - ax.c2p(a, 3)[0], height=4.3, fill_color=c, fill_opacity=0.10, stroke_width=0)
                         .move_to([(ax.c2p(a, 3)[0] + ax.c2p(b, 3)[0]) / 2, ax.c2p(2009, 12.5)[1], 0]) for _, a, b, c in eras])
        elabs = VGroup(*[T(n, 17, c if c != SLATE else "#8FA8BA", SANS, weight="BOLD").move_to(ax.c2p((a + b) / 2, 21.3)) for n, a, b, c in eras])
        elabs[1].shift(DOWN * 0.35)
        elabs[2].shift(UP * 0.0)
        curve = ax.plot_line_graph([p[0] for p in pts], [p[1] for p in pts], add_vertex_dots=False, line_color=BTC, stroke_width=4)
        self.play(Create(ax), FadeIn(xl), FadeIn(yl), FadeIn(ylab), run_time=1.2)
        self.say(L[0], Create(curve, run_time=L[0]["dur"] + 0.3, rate_func=linear))
        end = ax.c2p(pts[-1][0], pts[-1][1])
        big = T("≈ 10²¹ guesses / second", 30, BTC, MONO, weight="BOLD").move_to(ax.c2p(2021.6, 8.5))
        dot = Circle(radius=0.09, fill_color=BTC, fill_opacity=1, stroke_width=0).move_to(end)
        self.play(FadeIn(dot), FadeIn(big, shift=DOWN * 0.2), run_time=0.6)
        self.say(L[1], FadeIn(bands, run_time=0.8))
        per = L[1]["dur"] / 5
        for i in range(5):
            self.play(FadeIn(elabs[i], shift=DOWN * 0.15), bands[i].animate.set_fill(opacity=0.22), run_time=min(0.6, per))
            self.wait(max(0, per - 0.6))
        self.sync(S["end"] - 0.6)
        self.clear_stage(keep=[self.mobjects[0]], run_time=0.6)

    def lottery(self):
        S = SC["lottery"]
        L = S["lines"]
        k = self.kicker("03 · THE LOTTERY")
        img = HERE / "build" / "lottery_grid.png"
        if not img.exists():
            from PIL import Image, ImageDraw
            n, cell = 128, 10
            im = Image.new("RGBA", (n * cell, n * cell), INK)
            d = ImageDraw.Draw(im)
            win = (97, 41)
            for y in range(n):
                for x in range(n):
                    if y * n + x < ODDS:
                        d.rectangle([x * cell + 1, y * cell + 1, x * cell + cell - 2, y * cell + cell - 2], fill=BTC if (x, y) == win else "#4A443D")
            im.save(img)
        grid = ImageMobject(str(img)).set_height(5.0).shift(LEFT * 3.3 + DOWN * 0.05)
        win_pt = grid.get_corner(UL) + np.array([(97 + 0.5) / 128 * grid.width, -(41 + 0.5) / 128 * grid.height, 0])
        ring = Circle(radius=0.3, stroke_color=BTC, stroke_width=6).move_to(win_pt)
        odds = T(f"1 in {ODDS:,}", 76, BTC, SERIF, weight="BOLD").shift(RIGHT * 3.6 + UP * 1.2)
        sub = T("chance per year that a 1.2 TH/s\nhome miner in Hong Kong wins a block", 26, MUTED, line_spacing=0.9).next_to(odds, DOWN, buff=0.3)
        note = T(f"each square = one year · {ODDS:,} squares", 17, DIM, MONO).next_to(grid, UP, buff=0.15).align_to(grid, LEFT)
        # Fading ImageMobject hits a Pillow mode bug in Cairo; fade its cover instead.
        cover = Rectangle(width=grid.width + 0.1, height=grid.height + 0.1, fill_color=INK, fill_opacity=1, stroke_width=0).move_to(grid)
        self.add(grid, cover)
        self.play(FadeOut(cover), FadeIn(note), run_time=1.2)
        self.say(L[0], Write(odds, run_time=1.4))
        self.play(FadeIn(sub, shift=UP * 0.2), Create(ring), run_time=1.0)
        self.play(ring.animate.scale(1.5).set_stroke(opacity=0.0), run_time=1.0)
        ring2 = Circle(radius=0.3, stroke_color=BTC, stroke_width=6).move_to(win_pt)
        self.play(Create(ring2), run_time=0.6)
        self.sync(L[0]["end"])
        v = ValueTracker(0)
        cnt = always_redraw(lambda: T(f"{int(v.get_value())}", 76, PAPER, SERIF, weight="BOLD").move_to(RIGHT * 3.6 + DOWN * 1.3))
        lab = T("blocks still won by solo miners in 2025", 26, MUTED).move_to(RIGHT * 3.6 + DOWN * 2.15)
        self.say(L[1], FadeIn(cnt), FadeIn(lab))
        self.play(v.animate.set_value(SOLO25), run_time=min(2.2, L[1]["dur"]), rate_func=smooth)
        self.sync(S["end"] - 0.6)
        self.clear_stage(keep=[self.mobjects[0]], run_time=0.6)

    def fingerprint(self):
        S = SC["fingerprint"]
        L = S["lines"]
        k = self.kicker("04 · A FINGERPRINT IN EVERY BLOCK")
        rng = np.random.default_rng(7)
        bits = [int(b) for b in format(0x20000000, "032b")]
        cells = VGroup(*[Square(side_length=0.33, stroke_color=DIM, stroke_width=2, fill_color=INK2, fill_opacity=1) for _ in range(32)]).arrange(RIGHT, buff=0.06)
        cells.shift(UP * 1.35)
        nums = VGroup(*[T(str(b), 17, MUTED, MONO).move_to(c) for b, c in zip(bits, cells)])
        hdr = T("block header · version field · 32 bits", 22, MUTED, MONO).next_to(cells, UP, buff=0.3).align_to(cells, LEFT)
        roll = [31 - i for i in range(13, 29)]           # bit i sits at position 31 - i
        brace = Line(cells[roll[-1]].get_corner(DOWN + LEFT), cells[roll[0]].get_corner(DOWN + RIGHT), stroke_color=BTC, stroke_width=4).shift(DOWN * 0.12)
        btxt = T("bits 13-28: rolled by the miner's hardware", 22, BTC).next_to(brace, DOWN, buff=0.18)
        self.play(FadeIn(hdr), LaggedStart(*[FadeIn(VGroup(c, n)) for c, n in zip(cells, nums)], lag_ratio=0.03), run_time=1.3)
        self.say(L[0], *[cells[i].animate.set_stroke(BTC, 3) for i in roll])
        self.play(Create(brace), FadeIn(btxt), run_time=0.7)
        for _ in range(4):
            new = VGroup(*[T(str(rng.integers(0, 2)) if i in roll else str(bits[i]), 17, BTC if i in roll else MUTED, MONO).move_to(cells[i]) for i in range(32)])
            self.play(Transform(nums, new), run_time=0.35)
        self.sync(L[0]["end"])
        # Show block fullness beside the excluded coinbase tag.
        bar_bg = Rectangle(width=5.2, height=0.36, stroke_color=DIM, stroke_width=2, fill_color=INK2, fill_opacity=1).shift(LEFT * 3.0 + DOWN * 0.75)
        fill = Rectangle(width=0.01, height=0.36, stroke_width=0, fill_color=BTC, fill_opacity=1).align_to(bar_bg, LEFT).move_to(bar_bg, aligned_edge=LEFT)
        flab = T("block fullness · fee policy · witness share", 20, MUTED, MONO).next_to(bar_bg, UP, buff=0.18).align_to(bar_bg, LEFT)
        tag = VGroup(RoundedRectangle(corner_radius=0.08, width=3.2, height=0.75, stroke_color=BRICK, stroke_width=3),
                     T("/AntPool/", 28, PAPER, MONO)).shift(RIGHT * 4.0 + DOWN * 0.6)
        strike = Line(tag.get_left() + RIGHT * 0.15, tag.get_right() + LEFT * 0.15, stroke_color=BRICK, stroke_width=5)
        tlab = T("the name is the label,\nnever an input", 22, MUTED, line_spacing=0.9).next_to(tag, DOWN, buff=0.22)
        self.say(L[1], FadeIn(bar_bg), FadeIn(flab))
        self.play(fill.animate.stretch_to_fit_width(5.2 * 0.997).align_to(bar_bg, LEFT), run_time=1.4, rate_func=smooth)
        self.play(FadeIn(tag, shift=LEFT * 0.2), run_time=0.5)
        self.play(Create(strike), FadeIn(tlab), run_time=0.6)
        self.sync(S["end"] - 0.6)
        self.clear_stage(keep=[self.mobjects[0]], run_time=0.6)

    def questions(self):
        S = SC["questions"]
        L = S["lines"]
        k = self.kicker("05 · WHAT WE ASKED")
        v = ValueTracker(0)
        cnt = always_redraw(lambda: T(f"{int(v.get_value()):,}", 96, PAPER, SERIF, weight="BOLD").move_to(UP * 0.7))
        lab = T("Bitcoin blocks · January 2009 → November 2026", 28, MUTED).move_to(DOWN * 0.45)
        self.add(cnt)
        self.say(L[0], FadeIn(lab))
        self.play(v.animate.set_value(BLOCKS), run_time=min(2.6, L[0]["dur"]), rate_func=rate_functions.ease_out_cubic)
        self.sync(L[0]["end"] - 0.3)
        head = VGroup(T(f"{BLOCKS:,}", 44, PAPER, SERIF, weight="BOLD"), T("blocks mined", 24, MUTED)).arrange(RIGHT, buff=0.3, aligned_edge=DOWN).move_to(UP * 2.3)
        self.remove(cnt)
        big = T(f"{BLOCKS:,}", 96, PAPER, SERIF, weight="BOLD").move_to(UP * 0.7)
        self.add(big)
        self.play(Transform(big, head[0]), FadeOut(lab), FadeIn(head[1]), run_time=0.6)
        qs = [("Q1", "CLASSIFY", "Can behaviour alone\nreveal who mined\na block?", SLATE),
              ("Q2", "CLUSTER + RULES", "Does the data\nrediscover the eras\nof mining?", TEAL),
              ("Q3", "DECIDE", "Pool, solo lottery,\nor switch off,\nin Hong Kong?", BTC)]
        cards = []
        for i, (q, t, d, c) in enumerate(qs):
            box = Rectangle(width=3.9, height=2.7, stroke_color=LINE, stroke_width=2, fill_color=INK2, fill_opacity=1)
            topb = Rectangle(width=3.9, height=0.07, fill_color=c, fill_opacity=1, stroke_width=0).align_to(box, UP)
            badge = VGroup(Square(side_length=0.55, fill_color=c, fill_opacity=1, stroke_width=0), T(q, 20, PAPER if c != BTC else INK, MONO, weight="BOLD"))
            badge[1].move_to(badge[0])
            badge.move_to(box.get_corner(UL) + np.array([0.55, -0.6, 0]))
            title = T(t, 21, c if c != SLATE else "#8FA8BA", MONO, weight="BOLD").next_to(badge, RIGHT, buff=0.22)
            desc = T(d, 24, PAPER, line_spacing=0.85).move_to(box.get_center() + DOWN * 0.42).align_to(badge, LEFT)
            cards.append(VGroup(box, topb, badge, title, desc).move_to(LEFT * 4.25 + RIGHT * 4.25 * i + DOWN * 0.55))
        for i in range(3):
            self.say(L[i + 1], FadeIn(cards[i], shift=UP * 0.25, run_time=0.7))
        self.sync(S["end"] - 0.6)
        self.clear_stage(keep=[self.mobjects[0]], run_time=0.6)

    def title(self):
        S = SC["title"]
        L = S["lines"]
        lg = logo(1.5)
        word = VGroup(T("Hash", 92, PAPER, SERIF, weight="BOLD"), T("Atlas", 92, BTC, SERIF, weight="BOLD")).arrange(RIGHT, buff=0.04, aligned_edge=DOWN)
        lockup = VGroup(lg, word).arrange(RIGHT, buff=0.5).shift(UP * 1.1)
        sub = T("Can a small Bitcoin miner still win?", 40, PAPER, SERIF).next_to(lockup, DOWN, buff=0.55)
        rule = Line(LEFT * 4.5, RIGHT * 4.5, stroke_color=LINE, stroke_width=2).next_to(sub, DOWN, buff=0.5)
        foot = VGroup(T("Team HashAtlas · CDS3004 Data Mining · Lingnan University", 22, MUTED, MONO), T("cds3004.ansonlo.dev", 24, BTC, MONO)).arrange(DOWN, buff=0.2).next_to(rule, DOWN, buff=0.35)
        self.play(FadeIn(lg, scale=0.85), run_time=0.7)
        self.say(L[0], FadeIn(word, shift=LEFT * 0.3, run_time=0.8))
        self.play(FadeIn(sub, shift=UP * 0.2), Create(rule), run_time=0.9)
        self.play(FadeIn(foot), run_time=0.6)
        self.sync(TL["total_s"] - 0.9)
        self.play(FadeOut(self.cap), run_time=0.4)
        self.sync(TL["total_s"])
