"""Native KaTrain 1.20 explanation dock and evidence viewer.

Loaded by a small, reversible gui.kv import. The main game tree is never edited;
the continuation board is drawn from independently evaluated result snapshots.
All bridge callbacks are marshalled onto Kivy's main thread.

The viewer leads with the verdict, keeps the board and its playback on the
left, and splits the written explanation into short tabs of cards instead of
one long text, so the answer is visible without scrolling.
"""

from __future__ import annotations

import math

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.logger import Logger
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty, ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from katrain.core.lang import i18n
from katrain.gui.theme import Theme

from . import skin
from .bridge import KaTrainBridge


INK = (0.12, 0.16, 0.13, 1)
WOOD = (0.87, 0.73, 0.49, 1)
GREEN = (0.36, 0.80, 0.56, 1)
GREEN_DEEP = tuple(skin.ACTION)
MUTED = tuple(skin.TEXT_DIM)
PANEL = (0.098, 0.118, 0.150, 1)
CARD = tuple(skin.SURFACE)
CARD_ACTIVE = tuple(skin.SURFACE_HIGH)
KEY = tuple(skin.BUTTON)
LEVEL_COLORS = {
    "board": (0.38, 0.72, 0.93, 1),
    "search": GREEN,
    "reference": (0.94, 0.75, 0.38, 1),
    "tentative": (0.66, 0.70, 0.75, 1),
}
VERDICT_COLORS = {
    "best": GREEN,
    "equal": GREEN,
    "unstable": (0.56, 0.72, 0.93, 1),
    "slight": (0.82, 0.84, 0.40, 1),
    "inaccuracy": (0.96, 0.77, 0.32, 1),
    "mistake": (0.96, 0.57, 0.28, 1),
    "blunder": (0.92, 0.36, 0.33, 1),
}
# Search findings worth showing beside the verdict, most telling first.
KEY_REASONS = ("move-value", "followup-if-ignored", "close-candidates", "capture-versus-engine-choice",
               "opportunity-order", "tenuki-in-line", "ownership-group", "ownership-clue")
TABS = (("overview", "结论", "Verdict"), ("evidence", "依据", "Evidence"), ("line", "变化", "Line"),
        ("reference", "定式·术语", "Joseki & terms"), ("limits", "边界", "Limits"))
KEY_LEFT, KEY_RIGHT, KEY_SPACE, KEY_HOME, KEY_END = 276, 275, 32, 278, 279


DOCK_BUTTON_LABELS = {
    "cn": ("解释刚才一手", "解释 AI 一选"),
    "tw": ("解釋剛才一手", "解釋 AI 首選"),
    "en": ("Explain last move", "Explain AI choice"),
    "de": ("Letzten Zug erklären", "KI-Empfehlung erklären"),
    "fr": ("Expliquer le dernier coup", "Expliquer le choix de l’IA"),
    "ua": ("Пояснити останній хід", "Пояснити вибір ШІ"),
    "ru": ("Объяснить последний ход", "Объяснить выбор ИИ"),
    "ko": ("방금 둔 수 설명", "AI 추천 수 설명"),
    "jp": ("直前の一手を解説", "AIの第一候補を解説"),
    "tr": ("Son hamleyi açıkla", "YZ seçimini açıkla"),
    "es": ("Explicar la última jugada", "Explicar la elección de la IA"),
}


# KaTrain sizes its own text from the window, so on a large or high-DPI window
# fixed sp sizes look small. The viewer scales its fonts and fixed heights with
# the window height instead; the dock keeps the size gui.kv gives it.
_SCALE = [1.0]


def fs(value):
    return sp(value) * _SCALE[0]


def ds(value):
    return dp(value) * _SCALE[0]


def viewer_scale(window_height):
    return max(1.0, min(1.8, window_height / dp(760)))


def dock_button_labels(language):
    """Use KaTrain's locale IDs; unknown locales fall back to English."""
    return DOCK_BUTTON_LABELS.get(str(language or "en").lower(), DOCK_BUTTON_LABELS["en"])


def viewer_language(language):
    """The explanation text exists in Chinese and English."""
    return "zh" if str(language or "").lower() in ("cn", "tw") else "en"


def _gtp_xy(move, size):
    """Map GTP coordinates to top-left snapshot coordinates."""
    text = str(move or "").upper()
    if text in ("PASS", "RESIGN", ""):
        return None
    columns = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    try:
        x, y = columns.index(text[0]), size - int(text[1:])
    except (ValueError, IndexError):
        return None
    return (x, y) if 0 <= x < size and 0 <= y < size else None


def _canvas_text(text, x, y, font_size, color=(1, 1, 1, 1), anchor="center"):
    label = CoreLabel(text=str(text), font_name=Theme.DEFAULT_FONT, font_size=font_size)
    label.refresh()
    texture = label.texture
    Color(*color)
    Rectangle(
        texture=texture,
        pos=(x - (texture.width / 2 if anchor == "center" else 0), y - texture.height / 2),
        size=texture.size,
    )


def _signed(value, digits=1):
    number = round(float(value), digits)
    return f"{0.0 if number == 0 else number:+.{digits}f}"


def _flow(text):
    """Let Chinese text fill each line.

    Kivy only wraps at spaces, so a space between a move name and Chinese text
    would end the line early and leave it ragged. Non-breaking spaces make a
    Chinese paragraph wrap by character instead. Text with long Latin runs
    (English, URLs) keeps ordinary word wrapping.
    """
    text = str(text)
    cjk = sum(1 for char in text if "\u2e80" <= char <= "\u9fff" or "\uff00" <= char <= "\uffef")
    if cjk * 3 < len(text):
        return text
    return "\n".join(line.replace(" ", "\u00a0") for line in text.split("\n"))


def _wrap_label(text, font_size=None, color=None, bold=False):
    """A label whose height follows its wrapped text."""
    label = Label(text=_flow(text), font_name=Theme.DEFAULT_FONT, font_size=font_size or fs(15),
                  color=color or Theme.TEXT_COLOR, bold=bold, size_hint_y=None, halign="left", valign="top")
    label.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
    label.bind(texture_size=lambda widget, texture: setattr(widget, "height", texture[1]))
    return label


class RoundedBox(BoxLayout):
    """A raised card: shadow underneath, lit from above, optional coloured stripe on the left.

    `sunken=True` draws a well instead (used for the board caption).
    """

    def __init__(self, background=CARD, accent=None, radius=None, elevation=0.5, sunken=False, **kwargs):
        super().__init__(**kwargs)
        self._radius = ds(10) if radius is None else radius
        self._elevation, self._sunken = (0 if sunken else elevation), sunken
        with self.canvas.before:
            self._shadow_color, self._shadow = skin.drop_shadow(0, 0, 1, 1, 1, 0, 0.55 * min(1, self._elevation))
            self._background_color = Color(*background)
            self._background = RoundedRectangle(radius=[self._radius])
            Color(1, 1, 1, 1 if sunken else 0.75)
            self._gloss = RoundedRectangle(radius=[self._radius], texture=skin.inset() if sunken else skin.gloss())
            self._accent_color = Color(*(accent or (0, 0, 0, 0)))
            self._accent = RoundedRectangle(radius=[self._radius, 0, 0, self._radius])
            Color(*skin.EDGE)
            self._edge = Line(width=1)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_args):
        radius = min(self._radius, self.height / 2)
        self._background.pos, self._background.size = self.pos, self.size
        self._gloss.pos, self._gloss.size = self.pos, self.size
        self._accent.pos, self._accent.size = self.pos, (ds(4), self.height)
        self._edge.rounded_rectangle = (self.x, self.y, self.width, self.height, radius)
        skin.place_shadow(self._shadow, self.x, self.y, self.width, self.height,
                          ds(11) * self._elevation, ds(3) * self._elevation)

    def set_background(self, color):
        self._background_color.rgba = color


class KeyButton(ButtonBehavior, Label):
    """A raised key that goes down when pressed; `background_color` tints it."""

    background_color = ListProperty(list(KEY))

    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", Theme.DEFAULT_FONT)
        kwargs.setdefault("color", Theme.TEXT_COLOR)
        super().__init__(**kwargs)
        with self.canvas.before:
            self._shadow_color, self._shadow = skin.drop_shadow(0, 0, 1, 1, 1, 0, 0.55)
            self._face_color = Color(*self.background_color)
            self._face = RoundedRectangle()
            self._gloss_color = Color(1, 1, 1, 1)
            self._gloss = RoundedRectangle(texture=skin.gloss())
            Color(*skin.EDGE)
            self._edge = Line(width=1)
        self.bind(pos=self._sync, size=self._sync, state=self._sync, background_color=self._sync, disabled=self._sync)

    def _sync(self, *_args):
        down = self.state == "down"
        radius = min(self.height / 3.4, ds(11))
        self._face_color.rgba = [channel * (0.86 if down else 1) for channel in self.background_color[:3]] + [1]
        self._gloss_color.a = 0.25 if self.disabled else (0.45 if down else 1)
        self.opacity = 0.45 if self.disabled else 1
        sink = ds(1) if down else 0
        for shape in (self._face, self._gloss):
            shape.pos, shape.size, shape.radius = (self.x, self.y - sink), self.size, [radius]
        self._edge.rounded_rectangle = (self.x, self.y - sink, self.width, self.height, radius)
        depth = 0.15 if down or self.disabled else 0.9
        self._shadow_color.a = 0.55 * depth / 0.9 if skin.shadow() is not None else 0
        skin.place_shadow(self._shadow, self.x, self.y, self.width, self.height, ds(10) * depth, ds(3) * depth)


class Card(RoundedBox):
    """A vertical card that is exactly as tall as its content."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", (ds(14), ds(10), ds(12), ds(11)))
        kwargs.setdefault("spacing", ds(5))
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))


class ClickCard(ButtonBehavior, Card):
    pass


class Chip(Label):
    """A short coloured tag sized to its text."""

    def __init__(self, text, color, font_size=None, **kwargs):
        super().__init__(text=str(text), font_name=Theme.DEFAULT_FONT, font_size=font_size or fs(13),
                         color=INK, bold=True, size_hint=(None, None), **kwargs)
        with self.canvas.before:
            self._chip_color = Color(*color)
            self._chip = RoundedRectangle(radius=[ds(11)])
        self.bind(pos=self._sync, size=self._sync, texture_size=self._fit)
        self._fit()

    def _fit(self, *_args):
        if not self.text:  # no verdict yet: take no room in the header
            self.size = (0, ds(24))
            return
        self.size = (self.texture_size[0] + ds(20), max(ds(24), self.texture_size[1] + ds(6)))

    def _sync(self, *_args):
        self._chip.pos, self._chip.size = self.pos, self.size

    def restyle(self, text, color):
        self.text, self._chip_color.rgba = str(text), color


class SnapshotGoban(Widget):
    """Correct capture-aware preview; unlike KaTrain's overlay this removes stones."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._snapshot = None
        self._moves = []
        self._ply = 0
        self.bind(pos=self._redraw, size=self._redraw)

    def display(self, snapshot, moves=(), ply=0):
        self._snapshot, self._moves, self._ply = snapshot, list(moves), ply
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        if not self._snapshot:
            return
        size = int(self._snapshot.get("size", 19))
        side = min(self.width, self.height)
        x0, y0 = self.x + (self.width - side) / 2, self.y + (self.height - side) / 2
        margin = side * 0.065
        unit = (side - 2 * margin) / max(1, size - 1)
        left, bottom = x0 + margin, y0 + margin

        def point(x, y):
            return left + x * unit, bottom + (size - 1 - y) * unit

        stones = {}
        for stone in self._snapshot.get("stones", []):
            coords = (stone["x"], stone["y"]) if "x" in stone and "y" in stone else _gtp_xy(stone.get("move"), size)
            if coords is not None:
                stones[coords] = stone["player"]
        numbers = {}
        for index, step in enumerate(self._moves[: self._ply], 1):
            coords = _gtp_xy(step.get("move"), size)
            if coords is not None:
                numbers[coords] = (index, step.get("player"))
        latest = _gtp_xy(self._moves[self._ply - 1].get("move"), size) if 0 < self._ply <= len(self._moves) else None
        stars = [3, 9, 15] if size == 19 else [3, 6, 9] if size == 13 else [2, 4, 6] if size == 9 else []
        with self.canvas:
            wood = skin.image("kx_board.png")
            skin.drop_shadow(x0, y0 - ds(5), side, side + ds(5), ds(16), ds(6), 0.7)
            Color(*((0.52, 0.43, 0.34, 1) if wood else (0.55, 0.44, 0.27, 1)))
            RoundedRectangle(pos=(x0, y0 - ds(5)), size=(side, side), radius=[ds(7)], texture=wood)
            Color(*((1, 1, 1, 1) if wood else WOOD))
            RoundedRectangle(pos=(x0, y0), size=(side, side), radius=[ds(7)], texture=wood)
            Color(1, 0.96, 0.86, 0.45)
            Line(points=(x0 + ds(7), y0 + side - 1, x0 + side - ds(7), y0 + side - 1), width=1)
            Color(0.25, 0.16, 0.07, 0.9)
            for index in range(size):
                Line(points=(left, bottom + index * unit, left + (size - 1) * unit, bottom + index * unit), width=0.6)
                Line(points=(left + index * unit, bottom, left + index * unit, bottom + (size - 1) * unit), width=0.6)
            for x in stars:
                for y in stars:
                    px, py = point(x, y)
                    Ellipse(pos=(px - ds(1.6), py - ds(1.6)), size=(ds(3.2), ds(3.2)))
            for coords, player in stones.items():
                px, py = point(*coords)
                radius = unit * 0.475
                texture = skin.image("kx_stone_b.png" if player == "B" else "kx_stone_w.png")
                if texture is not None:  # the stone fills 88% of its texture; the rest is its shadow
                    half = radius / 0.88
                    Color(1, 1, 1, 1)
                    Rectangle(pos=(px - half, py - half), size=(2 * half, 2 * half), texture=texture)
                else:
                    Color(0, 0, 0, 0.16)
                    Ellipse(pos=(px - radius + ds(1), py - radius - ds(1)), size=(2 * radius, 2 * radius))
                    Color(*(INK if player == "B" else (0.98, 0.97, 0.93, 1)))
                    Ellipse(pos=(px - radius, py - radius), size=(2 * radius, 2 * radius))
                number = numbers.get(coords)
                if number and number[1] == player:
                    _canvas_text(number[0], px, py, unit * 0.48, (1, 1, 1, 1) if player == "B" else INK)
                if coords == latest:
                    Color(*GREEN)
                    Line(circle=(px, py, radius + ds(1.5)), width=ds(1.5))
            if self._ply == 0 and self._moves:
                target = _gtp_xy(self._moves[0].get("move"), size)
                if target is not None:
                    px, py = point(*target)
                    Color(0.18, 0.50, 0.32, 1)
                    Line(circle=(px, py, unit * 0.28), width=ds(1.6))
            # Coordinate labels help beginners locate moves in the explanation.
            for index in range(size):
                px, py = point(index, index)
                _canvas_text("ABCDEFGHJKLMNOPQRSTUVWXYZ"[index], px, y0 + side - margin * 0.33, side * 0.021, INK)
                _canvas_text(size - index, x0 + margin * 0.34, py, side * 0.021, INK)


class WinratePlot(Widget):
    """Measured per-position percentages, always in the original mover's perspective."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._steps, self._ply = [], 0
        self.bind(pos=self._redraw, size=self._redraw)

    def display(self, steps, ply):
        self._steps, self._ply = list(steps), ply
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        data = [(s["ply"], float(s["eval"]["winrate"])) for s in self._steps if s.get("eval", {}).get("winrate") is not None]
        if not data:
            return
        low = max(0, math.floor((min(v for _, v in data) - 3) / 5) * 5)
        high = min(100, max(low + 10, math.ceil((max(v for _, v in data) + 3) / 5) * 5))
        high = max(high, low + 1)
        # x + width, not the cached `right` alias: it can lag behind a resize in this callback.
        left, right = self.x + ds(40), self.x + self.width - ds(14)
        bottom, top = self.y + ds(24), self.y + self.height - ds(12)
        max_ply = max(1, max(p for p, _ in data))

        def point(ply, value):
            return left + ply / max_ply * (right - left), bottom + (value - low) / (high - low) * (top - bottom)

        with self.canvas:
            Color(*skin.SUNKEN)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[ds(10)])
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[ds(10)], texture=skin.inset())
            for index in range(3):
                value = low + index / 2 * (high - low)
                _, py = point(0, value)
                Color(1, 1, 1, 0.13)
                Line(points=(left, py, right, py), width=0.5)
                _canvas_text(f"{value:.0f}%", self.x + ds(19), py, fs(10), MUTED)
            Color(*GREEN)
            Line(points=[coordinate for p, v in data for coordinate in point(p, v)], width=1.4)
            for ply, value in data:
                px, py = point(ply, value)
                current = ply == self._ply
                radius = ds(5) if current else ds(2.5)
                Color(*((1, 1, 1, 1) if current else GREEN))
                Ellipse(pos=(px - radius, py - radius), size=(2 * radius, 2 * radius))
                if current:
                    Color(*GREEN)
                    Ellipse(pos=(px - ds(3.2), py - ds(3.2)), size=(ds(6.4), ds(6.4)))
                _canvas_text(ply, px, self.y + ds(10), fs(10), (1, 1, 1, 1) if current else MUTED)


class MeasuredProgress(Widget):
    """Only reports completed engine work; uses already-bundled Kivy primitives."""

    value = NumericProperty(0)
    max = NumericProperty(100)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, value=self._redraw, max=self._redraw)

    def _redraw(self, *_args):
        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1, 0.12)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.height / 2])
            Color(*GREEN)
            fraction = max(0, min(1, self.value / max(1, self.max)))
            RoundedRectangle(pos=self.pos, size=(self.width * fraction, self.height), radius=[self.height / 2])


class KaTrainExplainerPanel(BoxLayout):
    """Small dock; analysis and continuation playback stay inside KaTrain."""

    katrain = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", dp(4))
        kwargs.setdefault("padding", (dp(18), dp(5), dp(20), dp(10)))
        super().__init__(**kwargs)
        self._bridge = None
        self._initialization_error = None
        self._ready_logged = False
        self._language_app = None
        self._popup = None
        self._result = None
        self._branch_index = 0
        self._ply = 0
        self._busy = False
        self._play_event = None
        self._language = "zh"
        self._language_chosen = False
        self._error = None
        self._progress = None
        self._tab = "overview"
        self._buttons = []
        self._line_rows = []
        with self.canvas.before:  # the dock is a raised card like the panels below it
            self._dock_shadow_color, self._dock_shadow = skin.drop_shadow(0, 0, 1, 1, 1, 0, 0.55)
            Color(*skin.SURFACE)
            self._dock_face = RoundedRectangle()
            Color(1, 1, 1, 0.8)
            self._dock_gloss = RoundedRectangle(texture=skin.gloss())
            Color(*skin.EDGE)
            self._dock_edge = Line(width=1)
        self.bind(pos=self._sync_dock, size=self._sync_dock)
        heading = BoxLayout(size_hint_y=0.30, spacing=dp(6))
        self._dock_label = self._label("着法讲解 / Move explanation", sp(12), color=MUTED)
        self._dock_label.halign = "left"
        self._dock_label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        self._dock_status = self._label("", sp(12))
        self._dock_status.halign = "right"
        self._dock_status.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        heading.add_widget(self._dock_label)
        heading.add_widget(self._dock_status)
        self.add_widget(heading)
        actions = BoxLayout(size_hint_y=0.70, spacing=dp(8))
        initial_labels = dock_button_labels(getattr(App.get_running_app(), "language", "en"))
        self._actual_button = self._button(initial_labels[0], lambda *_: self.start_analysis("actual"),
                                           font_size=sp(12), background_color=list(skin.ACTION))
        self._ai_button = self._button(initial_labels[1], lambda *_: self.start_analysis("ai"),
                                       font_size=sp(12), background_color=list(skin.ACTION))
        self._reopen_button = self._button("↗", lambda *_: self._open_viewer(), font_size=sp(14),
                                           size_hint_x=None, width=dp(40), disabled=True)
        for button in (self._actual_button, self._ai_button, self._reopen_button):
            button.bind(height=lambda widget, height: setattr(widget, "font_size", max(sp(12), height * 0.40)))
        self._reopen_button.bind(height=lambda widget, height: setattr(widget, "width", height))
        for label in (self._dock_label, self._dock_status):
            label.bind(height=lambda widget, height: setattr(widget, "font_size", max(sp(11), height * 0.62)))
        actions.add_widget(self._actual_button)
        actions.add_widget(self._ai_button)
        actions.add_widget(self._reopen_button)
        self.add_widget(actions)
        # app.gui is assigned after the enclosing KaTrainGui is constructed.
        Clock.schedule_once(self._resolve_gui, 0)

    def _sync_dock(self, *_args):
        x, y, width, height = self.x + dp(8), self.y + dp(2), self.width - dp(18), self.height - dp(4)
        radius = dp(11)
        for shape in (self._dock_face, self._dock_gloss):
            shape.pos, shape.size, shape.radius = (x, y), (width, height), [radius]
        self._dock_edge.rounded_rectangle = (x, y, width, height, radius)
        skin.place_shadow(self._dock_shadow, x, y, width, height, dp(11), dp(3))

    @staticmethod
    def _label(text, font_size=None, height=None, color=None):
        kwargs = {"text": text, "font_name": Theme.DEFAULT_FONT, "font_size": font_size or fs(14),
                  "color": color or Theme.TEXT_COLOR}
        if height is not None:
            kwargs.update(size_hint_y=None, height=height)
        return Label(**kwargs)

    def _button(self, text, callback, font_size=None, **kwargs):
        button = KeyButton(text=text, font_size=font_size or fs(14), **kwargs)
        button.bind(on_release=callback)
        return button

    def _resolve_gui(self, *_args):
        app = App.get_running_app()
        gui = self.katrain or (getattr(app, "gui", None) if app else None)
        if gui is not None:
            self.katrain = gui
            self._bind_dock_language(app, gui)
            if self._bridge is None:
                try:
                    self._bridge = KaTrainBridge(gui)
                    self._initialization_error = None
                except Exception as error:
                    # A broken plugin setting must not stop KaTrain from opening.
                    self._initialization_error = str(error)
                    self._dock_status.text = "插件设置读取失败 / Plugin settings error"
            if self._bridge is not None and self.parent is not None and not self._ready_logged:
                Logger.info("KataGoExplainer: Native panel ready (KaTrain attached)")
                self._ready_logged = True
        return gui

    def _bind_dock_language(self, app, gui):
        if app is None or self._language_app is app:
            return
        if self._language_app is not None:
            self._language_app.unbind(language=self._on_app_language)
        self._language_app = app
        app.bind(language=self._on_app_language)
        # During build App.language still defaults to en; the saved setting is
        # applied by KaTrain's on_start. Read it now to avoid a startup mismatch.
        language = gui.config("general/lang", getattr(app, "language", "en"))
        self._update_dock_buttons(language)

    def _on_app_language(self, _app, language):
        self._update_dock_buttons(language)

    def _update_dock_buttons(self, language):
        labels = dock_button_labels(language)
        font = i18n.FONTS.get(str(language or "en").lower()) or Theme.DEFAULT_FONT
        self._actual_button.text, self._ai_button.text = labels
        self._actual_button.font_name = self._ai_button.font_name = font
        if not self._language_chosen:  # follow KaTrain until the viewer's own switch is used
            self._language = viewer_language(language)

    def _t(self, zh, en):
        return zh if self._language == "zh" else en

    def _localized(self, value):
        if isinstance(value, dict):
            return str(value.get(self._language, value.get("en", value.get("zh", ""))))
        return str(value or "")

    def _schedule(self, callback, *args):
        Clock.schedule_once(lambda _dt, fn=callback, values=args: fn(*values), 0)

    def _player_name(self, player):
        return self._t("黑", "Black") if player == "B" else self._t("白", "White")

    # ------------------------------------------------------------------ analysis

    def start_analysis(self, choice):
        if self._busy:
            self._open_viewer()
            return
        gui = self._resolve_gui()
        if gui is None:
            self._dock_status.text = "KaTrain 尚未就绪 / KaTrain is not ready"
            return
        if self._initialization_error:
            self._open_viewer()
            self._on_error({"zh": self._initialization_error, "en": self._initialization_error})
            return
        self._stop_play()
        self._result, self._error, self._progress = None, None, None
        self._branch_index, self._ply, self._tab = 0, 0, "overview"
        self._busy = True
        self._actual_button.disabled = self._ai_button.disabled = True
        self._reopen_button.disabled = False
        self._dock_status.color = MUTED
        self._dock_status.text = self._t("正在分析…", "Analyzing…")
        self._open_viewer()
        self._refresh_view()
        try:
            self._bridge.analyze(
                choice=choice,
                on_progress=lambda message, completed, total: self._schedule(self._on_progress, message, completed, total),
                on_result=lambda result: self._schedule(self._on_result, result),
                on_error=lambda error: self._schedule(self._on_error, error),
            )
        except Exception as error:
            self._on_error({"zh": str(error), "en": str(error)})

    def _on_progress(self, message, completed, total):
        self._progress = (message, completed, total)
        if self._popup:
            self._status_label.text = self._localized(message)
            self._progress_bar.value = 100 * completed / total if total else 0
            if not self._result and not self._error:
                self._title_label.text = self._localized(message)

    def _on_result(self, result):
        self._busy = False
        self._actual_button.disabled = self._ai_button.disabled = False
        self._result, self._error = result, None
        if not self._bridge.is_current(result):
            self._on_error({"zh": "棋局已改变，请在当前局面重新分析。", "en": "The game has changed. Analyze the current position again."})
            return
        verdict = (result.get("explanation") or {}).get("verdict") or {}
        self._dock_status.color = VERDICT_COLORS.get(verdict.get("level"), Theme.TEXT_COLOR)
        self._dock_status.text = f"{result.get('selected_move', '')} · " + (
            self._localized(verdict.get("label")) or self._t("讲解完成", "Explained"))
        self._refresh_view()

    def _on_error(self, error):
        self._busy = False
        self._actual_button.disabled = self._ai_button.disabled = False
        self._error = error
        self._dock_status.color = VERDICT_COLORS["mistake"]
        self._dock_status.text = self._t("分析未完成", "Analysis incomplete")
        self._refresh_view()

    # -------------------------------------------------------------------- viewer

    def _open_viewer(self):
        scale = viewer_scale(Window.height)
        if self._popup is not None and abs(scale - _SCALE[0]) < 0.08:
            self._popup.open()
            self._refresh_view()
            return
        if self._popup is not None:  # the window was resized: rebuild at the new size
            self._popup.dismiss()
            self._popup = None
        _SCALE[0] = scale
        content = BoxLayout(orientation="vertical", spacing=ds(8), padding=(ds(6), ds(4), ds(6), ds(6)))
        header = BoxLayout(size_hint_y=None, height=ds(40), spacing=ds(10))
        self._verdict_chip = Chip("", GREEN, font_size=fs(14), pos_hint={"center_y": 0.5})
        header.add_widget(self._verdict_chip)
        self._title_label = self._label("", fs(19))
        self._title_label.halign, self._title_label.valign = "left", "middle"
        self._title_label.shorten, self._title_label.shorten_from = True, "right"
        self._title_label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        header.add_widget(self._title_label)
        self._language_button = self._button("", self._toggle_language, size_hint_x=None, width=ds(92), font_size=fs(12))
        header.add_widget(self._language_button)
        self._close_button = self._button("", lambda *_: self._popup.dismiss(), size_hint_x=None, width=ds(76), font_size=fs(12))
        header.add_widget(self._close_button)
        content.add_widget(header)
        self._progress_bar = MeasuredProgress(max=100, value=0, size_hint_y=None, height=ds(4))
        content.add_widget(self._progress_bar)

        columns = BoxLayout(spacing=ds(14))
        self._left = left = BoxLayout(orientation="vertical", size_hint_x=0.41, spacing=ds(7))
        self._preview = SnapshotGoban()
        left.add_widget(self._preview)
        self._branch_row = BoxLayout(size_hint_y=None, height=ds(34), spacing=ds(5))
        left.add_widget(self._branch_row)
        playback = BoxLayout(size_hint_y=None, height=ds(34), spacing=ds(5))
        self._start_button = self._button("|<", lambda *_: self._set_ply(0))
        self._prev_button = self._button("<", lambda *_: self._set_ply(self._ply - 1))
        self._play_button = self._button("", self._toggle_play, font_size=fs(12), size_hint_x=1.5)
        self._next_button = self._button(">", lambda *_: self._set_ply(self._ply + 1))
        self._end_button = self._button(">|", lambda *_: self._set_ply(self._max_ply()))
        self._buttons = [self._start_button, self._prev_button, self._play_button, self._next_button, self._end_button]
        for button in self._buttons:
            playback.add_widget(button)
        left.add_widget(playback)
        self._caption = caption = RoundedBox(orientation="vertical", size_hint_y=None, height=ds(76), elevation=0.4,
                             padding=(ds(12), ds(8)), spacing=ds(2))
        self._step_label = self._label("", fs(14), height=ds(22))
        self._step_label.halign = "left"
        self._step_label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        caption.add_widget(self._step_label)
        self._step_text = self._label("", fs(12), color=MUTED)
        self._step_text.halign, self._step_text.valign = "left", "top"
        self._step_text.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        caption.add_widget(self._step_text)
        left.add_widget(caption)
        self._chart_label = self._label("", fs(11), height=ds(16), color=MUTED)
        self._chart_label.halign = "left"
        self._chart_label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        left.add_widget(self._chart_label)
        self._plot = WinratePlot(size_hint_y=None, height=ds(100))
        left.add_widget(self._plot)
        columns.add_widget(left)

        right = BoxLayout(orientation="vertical", size_hint_x=0.59, spacing=ds(8))
        self._tab_row = BoxLayout(size_hint_y=None, height=ds(34), spacing=ds(5))
        self._tab_buttons = {}
        for key, _zh, _en in TABS:
            button = self._button("", lambda _button, name=key: self._select_tab(name), font_size=fs(13))
            self._tab_buttons[key] = button
            self._tab_row.add_widget(button)
        right.add_widget(self._tab_row)
        self._scroll = ScrollView(do_scroll_x=False, bar_width=ds(5), scroll_type=["bars", "content"])
        self._cards = GridLayout(cols=1, size_hint_y=None, spacing=ds(8), padding=(0, 0, ds(8), ds(6)))
        self._cards.bind(minimum_height=self._cards.setter("height"))
        self._scroll.add_widget(self._cards)
        right.add_widget(self._scroll)
        self._status_label = self._label("", fs(11), height=ds(16), color=MUTED)
        self._status_label.halign = "left"
        self._status_label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        right.add_widget(self._status_label)
        columns.add_widget(right)
        content.add_widget(columns)
        self._popup = Popup(title="KataGo", title_font=Theme.DEFAULT_FONT, title_size=fs(13), title_color=MUTED,
                            content=content, size_hint=(0.95, 0.94), auto_dismiss=False,
                            separator_color=GREEN, separator_height=ds(1),
                            background="", background_color=PANEL)
        self._popup.bind(on_dismiss=self._on_dismiss, on_open=self._on_open)
        self._popup.open()
        self._refresh_view()

    def _on_open(self, *_args):
        Window.bind(on_key_down=self._on_key_down)

    def _on_dismiss(self, *_args):
        Window.unbind(on_key_down=self._on_key_down)
        self._stop_play()
        if self._bridge:
            self._bridge.clear_preview()

    def _on_key_down(self, _window, key, *_args):
        if not self._result or self._error:
            return False
        if key == KEY_LEFT:
            self._set_ply(self._ply - 1)
        elif key == KEY_RIGHT:
            self._set_ply(self._ply + 1)
        elif key == KEY_HOME:
            self._set_ply(0)
        elif key == KEY_END:
            self._set_ply(self._max_ply())
        elif key == KEY_SPACE:
            self._toggle_play()
        else:
            return False
        return True

    def _branches(self):
        return self._result.get("branches", []) if self._result else []

    def _branch(self):
        branches = self._branches()
        return branches[self._branch_index] if branches else {"steps": []}

    def _max_ply(self):
        return max((s.get("ply", 0) for s in self._branch().get("steps", [])), default=0)

    def _select_branch(self, index):
        self._stop_play()
        self._branch_index, self._ply = index, 0
        self._refresh_view()

    def _select_tab(self, name):
        self._tab = name
        self._refresh_view()
        self._scroll.scroll_y = 1

    def _set_ply(self, ply, stop=True):
        if stop:
            self._stop_play()
        self._ply = max(0, min(self._max_ply(), ply))
        self._refresh_board()

    def _show_step(self, ply, branch=0):
        """Jump the board to the step a card talks about."""
        self._stop_play()
        if branch != self._branch_index:
            self._branch_index = branch
            self._ply = max(0, min(self._max_ply(), ply))
            self._refresh_view()
        else:
            self._set_ply(ply)

    def _toggle_play(self, *_args):
        if self._play_event:
            self._stop_play()
            return
        if not self._result or self._error:
            return
        if self._ply >= self._max_ply():
            self._set_ply(0)
        self._play_event = Clock.schedule_interval(self._advance, 1.2)
        self._play_button.text = self._t("暂停", "Pause")

    def _advance(self, _dt):
        self._set_ply(self._ply + 1, stop=False)
        if self._ply >= self._max_ply():
            self._stop_play()
            return False

    def _stop_play(self):
        if self._play_event:
            self._play_event.cancel()
            self._play_event = None
        if hasattr(self, "_play_button"):
            self._play_button.text = self._t("播放", "Play")

    def _toggle_language(self, *_args):
        self._language = "en" if self._language == "zh" else "zh"
        self._language_chosen = True
        self._refresh_view()

    # ----------------------------------------------------------------- rendering

    def _usable(self):
        return bool(self._result) and not self._error

    def _refresh_view(self):
        if not self._popup:
            return
        if self._usable() and not self._bridge.is_current(self._result):
            self._on_error({"zh": "棋局已改变，请在当前局面重新分析。", "en": "The game has changed. Analyze the current position again."})
            return
        usable = self._usable()
        self._popup.title = self._t("KataGo · 着法讲解（← → 逐手，空格播放）", "KataGo · Move explanation (← → to step, Space to play)")
        self._language_button.text = "English" if self._language == "zh" else "中文"
        self._close_button.text = self._t("关闭", "Close")
        self._play_button.text = self._t("暂停", "Pause") if self._play_event else self._t("播放", "Play")
        for key, zh, en in TABS:
            button = self._tab_buttons[key]
            button.text = self._t(zh, en)
            button.disabled = not usable
            button.background_color = GREEN_DEEP if key == self._tab and usable else KEY
        self._branch_row.clear_widgets()
        for index, branch in enumerate(self._branches()):
            text = (self._t("讲解的这手 ", "Explained: ") if branch.get("id") == "selected"
                    else self._t("对比 ", "Compare: ")) + str(branch.get("move", ""))
            button = self._button(text, lambda _button, i=index: self._select_branch(i), font_size=fs(12))
            if index == self._branch_index:
                button.background_color = GREEN_DEEP
            self._branch_row.add_widget(button)
        self._render_header()
        self._render_cards()
        self._refresh_board()

    def _render_header(self):
        result = self._result or {}
        if self._usable():
            verdict = (result.get("explanation") or {}).get("verdict") or {}
            level = verdict.get("level")
            self._verdict_chip.restyle(self._localized(verdict.get("label")) or self._t("讲解", "Explained"),
                                       VERDICT_COLORS.get(level, GREEN))
            player = self._t("黑棋", "Black") if result.get("player") == "B" else self._t("白棋", "White")
            number = int(result.get("move_index", 0)) + 1
            self._title_label.text = self._t(f"{player} {result.get('selected_move', '')} · 第 {number} 手",
                                             f"{player} {result.get('selected_move', '')} · move {number}")
            self._progress_bar.value = 100
            engine = result.get("engine") or {}
            self._status_label.text = (self._t("分析完成", "Analysis complete") + f" · {result.get('elapsed_seconds', 0):.1f} s · "
                                       + str(engine.get("model", "")))
        else:
            self._verdict_chip.restyle("", GREEN)
            self._title_label.text = (self._t("分析未完成", "Analysis incomplete") if self._error
                                      else self._t("正在分析这手棋…", "Analyzing this move…"))
            if self._error:
                self._status_label.text, self._progress_bar.value = "", 0
            elif self._progress:
                self._on_progress(*self._progress)
            else:
                self._status_label.text, self._progress_bar.value = self._t("正在准备分析…", "Preparing analysis…"), 0

    def _refresh_board(self):
        """Update only what depends on the current step; cheap enough for playback."""
        if not self._popup:
            return
        usable = self._usable()
        for button in self._buttons:
            button.disabled = not usable
        self._left.opacity = 1 if usable else 0
        if not usable:
            self._preview.display(None)
            self._plot.display([], 0)
            self._step_label.text = self._step_text.text = self._chart_label.text = ""
            return
        self._start_button.disabled = self._prev_button.disabled = self._ply == 0
        self._next_button.disabled = self._end_button.disabled = self._ply >= self._max_ply()
        steps = self._branch().get("steps", [])
        current = next((s for s in steps if s.get("ply") == self._ply), {})
        try:
            snapshot = self._bridge.show_step(self._result, self._branch().get("id"), self._ply)
        except Exception as error:
            self._on_error({"zh": str(error), "en": str(error)})
            return
        self._preview.display(snapshot, [s for s in steps if s.get("ply", 0) > 0], self._ply)
        self._plot.display(steps, self._ply)
        metric = current.get("eval") or {}
        rate = f" · {metric['winrate']:.1f}%" if metric.get("winrate") is not None else ""
        if self._ply == 0:
            self._step_label.text = self._t("起始局面", "Starting position") + rate
            self._step_text.text = self._t("按 > 或 → 逐手查看搜索给出的变化；绿圈标出将要讲解的落点。",
                                           "Press > or → to step through the searched line; the green ring marks the move being explained.")
        else:
            self._step_label.text = (f"{self._t('变化', 'Step')} {self._ply}/{self._max_ply()} · "
                                     f"{self._player_name(current.get('player'))} {current.get('move')}{rate}")
            self._step_text.text = _flow(self._step_description(self._ply))
        color = self._t("黑棋", "Black") if self._result.get("player") == "B" else self._t("白棋", "White")
        self._chart_label.text = self._t(f"胜率 · 固定{color}视角 · 每点独立搜索", f"Win rate · {color}'s view · each point searched separately")
        for ply, row in self._line_rows:
            row.set_background(CARD_ACTIVE if ply == self._ply else CARD)

    def _step_description(self, ply):
        """The written note for a step of the explained line, without its heading and win rate."""
        if self._branch().get("id") != "selected":
            return self._t("另一选择的变化：对照同一局面下的不同走法。", "The alternative line: compare a different move from the same position.")
        notes = (self._result.get("explanation") or {}).get("continuation") or []
        if not 0 < ply <= len(notes):
            return ""
        text = self._localized(notes[ply - 1])
        for mark in ("。 ", ". "):  # drop the leading "变化第 N 手：黑方 E3。"
            head, found, rest = text.partition(mark)
            if found and len(head) < 40:
                text = rest
                break
        for tail in (" 此局面重新分析的", " Re-analysis of this position"):
            text = text.split(tail)[0]
        return text.strip()

    def _add(self, widget):
        self._cards.add_widget(widget)
        return widget

    def _section(self, text):
        self._add(_wrap_label(text, fs(12), MUTED))

    def _text_card(self, body, tag=None, accent=None, on_release=None, hint=None, body_size=None):
        card = (ClickCard if on_release else Card)(accent=accent)
        if tag or hint:
            top = BoxLayout(size_hint_y=None, height=ds(18), spacing=ds(8))
            tag_label = self._label(tag or "", fs(12), color=accent or MUTED)
            tag_label.halign, tag_label.bold = "left", True
            tag_label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
            top.add_widget(tag_label)
            if hint:
                hint_label = self._label(hint, fs(11), color=MUTED)
                hint_label.halign = "right"
                hint_label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
                top.add_widget(hint_label)
            card.add_widget(top)
        card.add_widget(_wrap_label(body, body_size or fs(15)))
        if on_release:
            card.bind(on_release=on_release)
        return self._add(card)

    def _reason_card(self, reason):
        level = reason.get("level")
        names = {"board": self._t("棋盘事实", "Board fact"), "search": self._t("搜索支持", "Search-supported"),
                 "tentative": self._t("推测，待验证", "Tentative"), "reference": self._t("定式参考", "Joseki reference")}
        ply = reason.get("ply")
        jump = isinstance(ply, int) and 0 < ply <= self._max_ply_of(0)
        self._text_card(self._localized(reason.get("text")), names.get(level, ""), LEVEL_COLORS.get(level, MUTED),
                        on_release=(lambda *_: self._show_step(ply, 0)) if jump else None,
                        hint=self._t(f"点击看第 {ply} 手", f"Click to show step {ply}") if jump else None)

    def _max_ply_of(self, branch_index):
        branches = self._branches()
        if not 0 <= branch_index < len(branches):
            return 0
        return max((s.get("ply", 0) for s in branches[branch_index].get("steps", [])), default=0)

    def _render_cards(self):
        self._cards.clear_widgets()
        self._line_rows = []
        if self._error:
            self._text_card(self._localized(self._error), self._t("分析未完成", "Analysis incomplete"), VERDICT_COLORS["mistake"])
            self._text_card(self._t("可以关闭窗口，在棋盘上选好局面后重新点击讲解按钮。", "Close this window, select the position on the board, and request the explanation again."))
            return
        if not self._result:
            self._text_card(self._t(
                "正在用 KaTrain 自己的 KataGo 引擎分析当前局面。\n\n解释刚才一手：从这手之前的局面讲解已经下出的着法。\n解释 AI 一选：从当前局面讲解引擎的第一选择。",
                "Analyzing the current position with KaTrain's own KataGo engine.\n\nLast move: explains the move just played, from the position before it.\nAI choice: explains the engine's first choice from the current position."),
                self._t("请稍候", "Please wait"), GREEN)
            return
        {"overview": self._render_overview, "evidence": self._render_evidence, "line": self._render_line,
         "reference": self._render_reference, "limits": self._render_limits}[self._tab]()

    def _tile_row(self, tiles):
        row = GridLayout(cols=len(tiles), size_hint_y=None, height=ds(70), spacing=ds(8))
        for caption, value, color in tiles:
            tile = RoundedBox(orientation="vertical", padding=(ds(12), ds(8)), spacing=ds(1))
            top = self._label(caption, fs(11), height=ds(16), color=MUTED)
            top.halign, top.shorten = "left", True
            top.bind(size=lambda widget, size: setattr(widget, "text_size", size))
            number = self._label(value, fs(18), color=color or Theme.TEXT_COLOR)
            number.halign, number.valign, number.shorten = "left", "middle", True
            number.bind(size=lambda widget, size: setattr(widget, "text_size", size))
            tile.add_widget(top)
            tile.add_widget(number)
            row.add_widget(tile)
        self._add(row)

    def _render_overview(self):
        result = self._result
        explanation = result.get("explanation") or {}
        verdict = explanation.get("verdict") or {}
        accent = VERDICT_COLORS.get(verdict.get("level"), GREEN)
        self._text_card(self._localized(explanation.get("summary")), accent=accent, body_size=fs(17))
        selected, alternative = result.get("selected") or {}, result.get("alternative") or {}
        difference = result.get("comparison") or {}
        move, points = result.get("selected_move", ""), self._t("目", "pts")
        tiles = [(self._t(f"{move} 胜率", f"{move} win rate"), f"{selected.get('winrate', 0):.1f}%", None),
                 (self._t("预计目差", "Score lead"), f"{_signed(selected.get('score_lead', 0))} {points}", None)]
        if alternative and difference:
            tiles.append((self._t(f"对比 {alternative.get('move')}（胜率·目）", f"vs {alternative.get('move')} (win · pts)"),
                          f"{_signed(difference.get('winrate_pp', 0))}% · {_signed(difference.get('score_points', 0))}", accent))
        skipped = ((result.get("tenuki") or {}).get("pass") or {}).get("eval") or {}
        if skipped.get("score_lead") is not None and selected.get("score_lead") is not None:
            worth = selected["score_lead"] - skipped["score_lead"]
            tiles.append((self._t("这手约值（对比停一手）", "Worth (vs passing)"), f"{worth:.1f} {points}", None))
        self._tile_row(tiles)
        reasons = {reason.get("id"): reason for reason in explanation.get("reasons", [])}
        chosen = [reasons[key] for key in KEY_REASONS if key in reasons][:4]
        if chosen:
            self._section(self._t("搜索里最能说明问题的几点", "What the search shows most clearly"))
            for reason in chosen:
                self._reason_card(reason)
        joseki = explanation.get("joseki") or []
        if joseki:
            self._text_card(self._localized(joseki[0].get("name")) + " · " + self._localized(joseki[0].get("move_role")),
                            self._t("定式参考", "Joseki reference"), LEVEL_COLORS["reference"],
                            on_release=lambda *_: self._select_tab("reference"), hint=self._t("点击看手顺", "Click for the sequence"))
        self._section(self._t("左侧可逐手播放变化；“依据”列出全部理由及其可信程度。",
                              "Replay the line on the left; “Evidence” lists every reason with how far it can be trusted."))

    def _render_evidence(self):
        reasons = (self._result.get("explanation") or {}).get("reasons", [])
        self._section(self._t("蓝色是可在棋盘上核对的事实，绿色来自本次搜索，黄色是定式参考，灰色只是推测。",
                              "Blue is checkable on the board, green comes from this search, yellow is joseki reference, grey is only tentative."))
        for reason in reasons:
            self._reason_card(reason)

    def _render_line(self):
        branch = self._branch()
        notes = (self._result.get("explanation") or {}).get("continuation") or []
        self._section(self._t("点击任意一手，棋盘跳到该步。胜率固定为被讲解一方的视角。",
                              "Click a step to show it on the board. Win rates keep the explained player's perspective."))
        previous = None
        for step in branch.get("steps", []):
            ply, metric = step.get("ply", 0), step.get("eval") or {}
            rate = metric.get("winrate")
            delta = "" if previous is None or rate is None else f"  Δ {_signed(rate - previous)}"
            title = (self._t("起始局面", "Starting position") if ply == 0
                     else f"{ply}. {self._player_name(step.get('player'))} {step.get('move')}")
            row = ClickCard(background=CARD_ACTIVE if ply == self._ply else CARD, padding=(ds(14), ds(8), ds(12), ds(9)))
            top = BoxLayout(size_hint_y=None, height=ds(20), spacing=ds(8))
            name = self._label(title, fs(14))
            name.halign = "left"
            name.bind(size=lambda widget, size: setattr(widget, "text_size", size))
            value = self._label("" if rate is None else f"{rate:.1f}%{delta}", fs(13), color=MUTED)
            value.halign = "right"
            value.bind(size=lambda widget, size: setattr(widget, "text_size", size))
            top.add_widget(name)
            top.add_widget(value)
            row.add_widget(top)
            if ply and branch.get("id") == "selected" and ply <= len(notes):
                text = self._step_description(ply)
                if text:
                    row.add_widget(_wrap_label(text, fs(13), MUTED))
            row.bind(on_release=lambda _row, target=ply: self._set_ply(target))
            self._line_rows.append((ply, row))
            self._add(row)
            if rate is not None:
                previous = rate

    def _render_reference(self):
        explanation = self._result.get("explanation") or {}
        joseki, terms = explanation.get("joseki") or [], explanation.get("terms") or []
        if not joseki and not terms:
            self._text_card(self._t("这手没有匹配到已收录的定式前缀，也没有需要解释的术语。",
                                    "This move matches no cataloged joseki prefix and uses no glossary term."))
            return
        if joseki:
            self._section(self._t("定式参考手顺独立于左侧的 KataGo 搜索变化；定式名称不等于本局最佳选择。★ 是正在讲解的一手。",
                                  "Joseki reference sequences are separate from the KataGo line on the left; a joseki name is not the best move in this game. ★ marks the explained move."))
        for match in joseki:
            card = Card(accent=LEVEL_COLORS["reference"])
            card.add_widget(_wrap_label(self._localized(match.get("name")), fs(16)))
            metadata = " · ".join(part for part in (self._localized(match.get(key)) for key in ("corner", "stage", "relation")) if part)
            card.add_widget(_wrap_label(metadata, fs(12), MUTED))
            role = self._localized(match.get("move_role"))
            if role:
                card.add_widget(_wrap_label(self._t("本手作用：", "This move's role: ") + role, fs(14), LEVEL_COLORS["reference"]))
            if self._localized(match.get("move_explanation")):
                card.add_widget(_wrap_label(self._localized(match.get("move_explanation")), fs(14)))
            sequence = []
            for index, step in enumerate(match.get("reference_line") or [], 1):
                player = self._t("黑", "B") if step.get("player") == "B" else self._t("白", "W")
                role = self._localized(step.get("role"))
                sequence.append(("★ " if step.get("selected") else "    ") + f"{step.get('ply', index)}. {player} {step.get('move', '')}"
                                + (f" — {role}" if role else ""))
            if sequence:
                card.add_widget(_wrap_label("\n".join(sequence), fs(13)))
            for source in match.get("sources") or []:
                card.add_widget(_wrap_label(self._t("出处：", "Source: ") + self._localized(source.get("title"))
                                            + ("\n" + str(source.get("url")) if source.get("url") else ""), fs(11), MUTED))
            for note in match.get("notes") or []:
                card.add_widget(_wrap_label("• " + self._localized(note), fs(12), MUTED))
            self._add(card)
        if terms:
            self._section(self._t("本次讲解用到的术语", "Terms used in this explanation"))
        for term in terms:
            name, definition = self._localized(term.get("term")), self._localized(term.get("definition"))
            if name:
                card = Card(padding=(ds(14), ds(8), ds(12), ds(9)))
                card.add_widget(_wrap_label(name, fs(14), GREEN))
                if definition:
                    card.add_widget(_wrap_label(definition, fs(13)))
                self._add(card)

    def _render_limits(self):
        result = self._result
        explanation = result.get("explanation") or {}
        budgets, engine = result.get("budgets") or {}, result.get("engine") or {}
        self._text_card(self._t(
            f"引擎：{engine.get('version', '')} · {engine.get('model', '')}\n"
            f"根搜索 {budgets.get('root_visits', '—')} · 候选补搜 {budgets.get('candidate_visits', '—')} · "
            f"逐手评估 {budgets.get('trace_visits', '—')} · 脱先对比 {budgets.get('tenuki_visits', '—')} visits · "
            f"耗时 {result.get('elapsed_seconds', 0):.1f} 秒",
            f"Engine: {engine.get('version', '')} · {engine.get('model', '')}\n"
            f"Root {budgets.get('root_visits', '—')} · candidates {budgets.get('candidate_visits', '—')} · "
            f"per step {budgets.get('trace_visits', '—')} · tenuki test {budgets.get('tenuki_visits', '—')} visits · "
            f"{result.get('elapsed_seconds', 0):.1f} s"),
            self._t("本次搜索", "This search"), GREEN, body_size=fs(13))
        for note in list(explanation.get("limitations", [])) + list(result.get("warnings", [])):
            self._text_card(self._localized(note), body_size=fs(14))


Factory.register("KaTrainExplainerPanel", cls=KaTrainExplainerPanel)
