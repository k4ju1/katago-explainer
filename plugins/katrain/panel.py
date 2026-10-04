"""Native KaTrain 1.20 explanation dock and evidence viewer.

Loaded by a small, reversible gui.kv import. The main game tree is never edited;
the continuation board is drawn from independently evaluated result snapshots.
All bridge callbacks are marshalled onto Kivy's main thread.
"""

from __future__ import annotations

import math

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.logger import Logger
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.utils import escape_markup

from katrain.core.lang import i18n
from katrain.gui.theme import Theme

from .bridge import KaTrainBridge


INK = (0.12, 0.16, 0.13, 1)
WOOD = (0.87, 0.73, 0.49, 1)
GREEN = (0.31, 0.78, 0.53, 1)
MUTED = (0.69, 0.75, 0.79, 1)


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


def dock_button_labels(language):
    """Use KaTrain's locale IDs; unknown locales fall back to English."""
    return DOCK_BUTTON_LABELS.get(str(language or "en").lower(), DOCK_BUTTON_LABELS["en"])


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
        stars = [3, 9, 15] if size == 19 else [3, 6, 9] if size == 13 else [2, 4, 6] if size == 9 else []
        with self.canvas:
            Color(*WOOD)
            Rectangle(pos=(x0, y0), size=(side, side))
            Color(0.36, 0.29, 0.17, 0.85)
            for index in range(size):
                Line(points=(left, bottom + index * unit, left + (size - 1) * unit, bottom + index * unit), width=0.6)
                Line(points=(left + index * unit, bottom, left + index * unit, bottom + (size - 1) * unit), width=0.6)
            for x in stars:
                for y in stars:
                    px, py = point(x, y)
                    Ellipse(pos=(px - dp(1.6), py - dp(1.6)), size=(dp(3.2), dp(3.2)))
            for coords, player in stones.items():
                px, py = point(*coords)
                radius = unit * 0.46
                Color(0, 0, 0, 0.16)
                Ellipse(pos=(px - radius + dp(1), py - radius - dp(1)), size=(2 * radius, 2 * radius))
                Color(*(INK if player == "B" else (0.98, 0.97, 0.93, 1)))
                Ellipse(pos=(px - radius, py - radius), size=(2 * radius, 2 * radius))
                number = numbers.get(coords)
                if number and number[1] == player:
                    _canvas_text(number[0], px, py, unit * 0.48, (1, 1, 1, 1) if player == "B" else INK)
            if self._ply == 0 and self._moves:
                target = _gtp_xy(self._moves[0].get("move"), size)
                if target is not None:
                    px, py = point(*target)
                    Color(0.18, 0.50, 0.32, 1)
                    Line(circle=(px, py, unit * 0.28), width=dp(1.6))
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
        left, right = self.x + dp(36), self.right - dp(12)
        bottom, top = self.y + dp(23), self.top - dp(14)
        max_ply = max(1, max(p for p, _ in data))

        def point(ply, value):
            return left + ply / max_ply * (right - left), bottom + (value - low) / (high - low) * (top - bottom)

        with self.canvas:
            for index in range(3):
                value = low + index / 2 * (high - low)
                _, py = point(0, value)
                Color(1, 1, 1, 0.13)
                Line(points=(left, py, right, py), width=0.5)
                _canvas_text(f"{value:.0f}%", self.x + dp(16), py, sp(10), MUTED)
            Color(*GREEN)
            Line(points=[coordinate for p, v in data for coordinate in point(p, v)], width=1.4)
            for ply, value in data:
                px, py = point(ply, value)
                radius = dp(4) if ply == self._ply else dp(2.5)
                Color(*GREEN)
                Ellipse(pos=(px - radius, py - radius), size=(2 * radius, 2 * radius))
                _canvas_text(ply, px, self.y + dp(9), sp(10), MUTED)


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
            Rectangle(pos=self.pos, size=self.size)
            Color(*GREEN)
            fraction = max(0, min(1, self.value / max(1, self.max)))
            Rectangle(pos=self.pos, size=(self.width * fraction, self.height))


class KaTrainExplainerPanel(BoxLayout):
    """Small dock; analysis and continuation playback stay inside KaTrain."""

    katrain = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", dp(3))
        kwargs.setdefault("padding", (dp(6), dp(3)))
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
        self._error = None
        self._progress = None
        self._buttons = []
        self._dock_label = self._label("着法解释 / Move explanation", sp(12), height=dp(19))
        self.add_widget(self._dock_label)
        actions = BoxLayout(spacing=dp(5))
        initial_labels = dock_button_labels(getattr(App.get_running_app(), "language", "en"))
        self._actual_button = self._button(initial_labels[0], lambda *_: self.start_analysis("actual"), font_size=sp(12))
        self._ai_button = self._button(initial_labels[1], lambda *_: self.start_analysis("ai"), font_size=sp(12))
        actions.add_widget(self._actual_button)
        actions.add_widget(self._ai_button)
        self.add_widget(actions)
        # app.gui is assigned after the enclosing KaTrainGui is constructed.
        Clock.schedule_once(self._resolve_gui, 0)

    @staticmethod
    def _label(text, font_size=sp(14), height=None, color=None):
        kwargs = {"text": text, "font_name": Theme.DEFAULT_FONT, "font_size": font_size, "color": color or Theme.TEXT_COLOR}
        if height is not None:
            kwargs.update(size_hint_y=None, height=height)
        return Label(**kwargs)

    def _button(self, text, callback, font_size=sp(14), **kwargs):
        button = Button(text=text, font_name=Theme.DEFAULT_FONT, font_size=font_size, background_normal="", background_color=Theme.BOX_BACKGROUND_COLOR, **kwargs)
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
                    self._dock_label.text = "插件设置读取失败 / Plugin settings error"
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

    def _t(self, zh, en):
        return zh if self._language == "zh" else en

    def _localized(self, value):
        if isinstance(value, dict):
            return str(value.get(self._language, value.get("en", value.get("zh", ""))))
        return str(value or "")

    def _schedule(self, callback, *args):
        Clock.schedule_once(lambda _dt, fn=callback, values=args: fn(*values), 0)

    def start_analysis(self, choice):
        if self._busy:
            self._open_viewer()
            return
        gui = self._resolve_gui()
        if gui is None:
            self._dock_label.text = "KaTrain 尚未就绪 / KaTrain is not ready"
            return
        if self._initialization_error:
            self._open_viewer()
            self._on_error({"zh": self._initialization_error, "en": self._initialization_error})
            return
        self._stop_play()
        self._result, self._error, self._progress = None, None, None
        self._branch_index, self._ply = 0, 0
        self._busy = True
        self._actual_button.disabled = self._ai_button.disabled = True
        self._dock_label.text = "正在分析 / Analyzing…"
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

    def _open_viewer(self):
        if self._popup is not None:
            self._popup.open()
            return
        content = BoxLayout(orientation="vertical", spacing=dp(9), padding=dp(8))
        top = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        self._status_label = self._label("")
        top.add_widget(self._status_label)
        self._language_button = self._button("中文 / English", self._toggle_language, size_hint_x=None, width=dp(136), font_size=sp(12))
        top.add_widget(self._language_button)
        self._close_button = self._button("关闭 / Close", lambda *_: self._popup.dismiss(), size_hint_x=None, width=dp(100), font_size=sp(12))
        top.add_widget(self._close_button)
        content.add_widget(top)
        self._progress_bar = MeasuredProgress(max=100, value=0, size_hint_y=None, height=dp(5))
        content.add_widget(self._progress_bar)

        columns = BoxLayout(spacing=dp(16))
        left = BoxLayout(orientation="vertical", size_hint_x=0.4, spacing=dp(7))
        self._preview = SnapshotGoban()
        left.add_widget(self._preview)
        self._branch_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(5))
        left.add_widget(self._branch_row)
        playback = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(5))
        self._start_button = self._button("|<", lambda *_: self._set_ply(0))
        self._prev_button = self._button("<", lambda *_: self._set_ply(self._ply - 1))
        self._play_button = self._button("播放 / Play", self._toggle_play, font_size=sp(12), size_hint_x=1.5)
        self._next_button = self._button(">", lambda *_: self._set_ply(self._ply + 1))
        self._end_button = self._button(">|", lambda *_: self._set_ply(self._max_ply()))
        self._buttons = [self._start_button, self._prev_button, self._play_button, self._next_button, self._end_button]
        for button in self._buttons:
            playback.add_widget(button)
        left.add_widget(playback)
        self._step_label = self._label("", sp(13), height=dp(30))
        left.add_widget(self._step_label)
        self._chart_label = self._label("", sp(12), height=dp(22), color=MUTED)
        left.add_widget(self._chart_label)
        self._plot = WinratePlot(size_hint_y=None, height=dp(128))
        left.add_widget(self._plot)
        self._chart_note = self._label("", sp(11), height=dp(48), color=MUTED)
        self._chart_note.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
        left.add_widget(self._chart_note)
        columns.add_widget(left)

        scroll = ScrollView(size_hint_x=0.6, do_scroll_x=False, bar_width=dp(5))
        self._report = Label(text="", font_name=Theme.DEFAULT_FONT, font_size=sp(16), size_hint_y=None, halign="left", valign="top", markup=True, padding=(dp(9), dp(9)), color=Theme.TEXT_COLOR)
        self._report.bind(width=lambda widget, width: setattr(widget, "text_size", (max(dp(10), width - dp(18)), None)))
        self._report.bind(texture_size=lambda widget, texture: setattr(widget, "height", texture[1] + dp(18)))
        scroll.add_widget(self._report)
        columns.add_widget(scroll)
        content.add_widget(columns)
        self._popup = Popup(title="KataGo 着法解释 / Move explanation", title_font=Theme.DEFAULT_FONT, title_size=sp(18), content=content, size_hint=(0.94, 0.92), auto_dismiss=False, separator_color=GREEN)
        self._popup.bind(on_dismiss=self._on_dismiss)
        self._popup.open()
        self._refresh_view()

    def _on_progress(self, message, completed, total):
        self._progress = (message, completed, total)
        if self._popup:
            self._status_label.text = self._localized(message) + (f" · {completed}/{total}" if total else "")
            self._progress_bar.value = 100 * completed / total if total else 0

    def _on_result(self, result):
        self._busy = False
        self._actual_button.disabled = self._ai_button.disabled = False
        self._result, self._error = result, None
        self._dock_label.text = "分析完成 / Analysis complete"
        if not self._bridge.is_current(result):
            self._on_error({"zh": "棋局已改变，请在当前局面重新分析。", "en": "The game has changed. Analyze the current position again."})
            return
        self._refresh_view()

    def _on_error(self, error):
        self._busy = False
        self._actual_button.disabled = self._ai_button.disabled = False
        self._error = error
        self._dock_label.text = "分析未完成 / Analysis incomplete"
        self._refresh_view()

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

    def _set_ply(self, ply, stop=True):
        if stop:
            self._stop_play()
        self._ply = max(0, min(self._max_ply(), ply))
        self._refresh_view()

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

    def _on_dismiss(self, *_args):
        self._stop_play()
        if self._bridge:
            self._bridge.clear_preview()

    def _toggle_language(self, *_args):
        self._language = "en" if self._language == "zh" else "zh"
        self._refresh_view()

    def _refresh_view(self):
        if not self._popup:
            return
        self._popup.title = self._t("KataGo · 为什么这样下", "KataGo · Why this move")
        self._language_button.text = "中文 → English" if self._language == "zh" else "English → 中文"
        self._close_button.text = self._t("关闭", "Close")
        self._play_button.text = self._t("暂停", "Pause") if self._play_event else self._t("播放", "Play")
        self._branch_row.clear_widgets()
        for index, branch in enumerate(self._branches()):
            button = self._button(self._localized(branch.get("label")), lambda _button, i=index: self._select_branch(i), font_size=sp(12))
            if index == self._branch_index:
                button.background_color = (0.19, 0.43, 0.31, 1)
            self._branch_row.add_widget(button)
        usable = bool(self._result) and not self._error
        if usable and not self._bridge.is_current(self._result):
            self._on_error({"zh": "棋局已改变，请在当前局面重新分析。", "en": "The game has changed. Analyze the current position again."})
            return
        for button in self._buttons:
            button.disabled = not usable
        if usable:
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
            metric = current.get("eval", {})
            position = self._t("起始局面", "Starting position") if self._ply == 0 else f"{self._t('变化', 'Step')} {self._ply}/{self._max_ply()} · {current.get('player')} {current.get('move')}"
            self._step_label.text = position + (f" · {metric['winrate']:.1f}%" if metric.get("winrate") is not None else "")
            color = self._t("黑棋", "Black") if self._result.get("player") == "B" else self._t("白棋", "White")
            self._chart_label.text = self._t("胜率变化 · 固定", "Winrate · fixed") + " " + color + self._t("视角", " perspective")
            self._chart_note.text = self._t("每个点来自独立搜索。评估波动不能直接归因于某一手；数字为后续手顺。", "Each point is searched independently. Evaluation drift is not a move's causal contribution. Numbers show the continuation.")
            self._progress_bar.value = 100
            self._status_label.text = self._t("分析完成", "Analysis complete") + f" · {self._result.get('elapsed_seconds', 0):.1f} s"
        elif self._error:
            self._status_label.text = self._t("分析未完成", "Analysis incomplete")
            self._preview.display(None)
            self._plot.display([], 0)
            self._step_label.text = self._chart_label.text = self._chart_note.text = ""
            self._progress_bar.value = 0
        elif self._progress:
            self._on_progress(*self._progress)
        else:
            self._status_label.text = self._t("正在准备分析…", "Preparing analysis…")
            self._preview.display(None)
            self._plot.display([], 0)
            self._step_label.text = self._chart_label.text = self._chart_note.text = ""
            self._progress_bar.value = 0
        self._update_text()

    def _update_text(self):
        if not hasattr(self, "_report"):
            return
        if self._error:
            self._report.text = "[b]" + escape_markup(self._t("分析未完成", "Analysis incomplete")) + "[/b]\n\n" + escape_markup(self._localized(self._error))
            return
        if not self._result:
            self._report.text = escape_markup(self._t("正在读取 KaTrain 当前棋局并请求 KataGo 分析。\n\n解释刚才一手：从这手之前的局面解释已经下出的着法。\n解释 AI 一选：从当前局面解释引擎下一手的第一选择。\n\n结果会显示棋理证据、真实后续变化与固定视角的胜率。", "Reading the current KaTrain game and requesting KataGo analysis.\n\nLast move: explain the move just played, from the position before it.\nAI choice: explain the engine's first choice from the current position.\n\nThe result will show evidence, real continuations, and winrates in a fixed perspective."))
            return
        result = self._result
        explanation = result.get("explanation", {})
        sections = []

        def heading(text):
            sections.append("[b][color=8cdda9]" + escape_markup(text) + "[/color][/b]")

        heading(self._localized(explanation.get("title")) or self._t("为什么这样下", "Why this move"))
        sections.append(escape_markup(self._localized(explanation.get("summary"))))
        joseki = explanation.get("joseki") or []
        if joseki:
            heading(self._t("定式关联", "Joseki reference"))
            sections.append(escape_markup(self._t("以下是定式参照手顺，独立于左侧 KataGo 搜索变化；定式名称不等于当前全局最佳选择。★ 标记正在讲解的一手。", "These are joseki reference patterns, separate from the KataGo search lines on the left. A recognized joseki does not establish the best whole-board choice. ★ marks the move being explained.")))
            for match in joseki:
                sections.append("[b]" + escape_markup(self._localized(match.get("name"))) + "[/b]")
                metadata = [self._localized(match.get(key)) for key in ("corner", "stage", "relation")]
                sections.append(escape_markup(" · ".join(part for part in metadata if part)))
                role = self._localized(match.get("move_role"))
                if role:
                    sections.append(escape_markup(self._t("本手作用：", "This move's role: ") + role))
                move_explanation = self._localized(match.get("move_explanation"))
                if move_explanation:
                    sections.append(escape_markup(move_explanation))
                reference = []
                for index, step in enumerate(match.get("reference_line") or [], 1):
                    player = self._t("黑", "B") if step.get("player") == "B" else self._t("白", "W")
                    mark = "★ " if step.get("selected") else ""
                    point = f"{mark}{step.get('ply', index)}. {player} {step.get('move', '')}"
                    role = self._localized(step.get("role"))
                    reference.append(point + (" — " + role if role else ""))
                if reference:
                    sections.append("[b]" + escape_markup(self._t("定式参考手顺", "Joseki reference sequence")) + "[/b]\n" + escape_markup("\n".join(reference)))
                for source in match.get("sources") or []:
                    title, url = self._localized(source.get("title")), str(source.get("url") or "")
                    sections.append(escape_markup(self._t("出处：", "Source: ") + title + ("\n" + url if url else "")))
                for note in match.get("notes") or []:
                    sections.append("• " + escape_markup(self._localized(note)))
        terms = explanation.get("terms") or []
        if terms:
            heading(self._t("围棋术语", "Go terminology"))
            for term in terms:
                name, definition = self._localized(term.get("term")), self._localized(term.get("definition"))
                if name:
                    sections.append("[b]" + escape_markup(name) + "[/b]" + ("\n" + escape_markup(definition) if definition else ""))
        heading(self._t("棋理与证据", "Reasons and evidence"))
        for index, reason in enumerate(explanation.get("reasons", []), 1):
            level = {"board": self._t("棋盘事实", "Board fact"), "search": self._t("搜索支持", "Search-supported"), "tentative": self._t("待进一步验证", "Tentative"), "reference": self._t("定式参考", "Joseki reference")}.get(reason.get("level"), "")
            sections.append(f"[b]{index}. {escape_markup(level)}[/b]\n{escape_markup(self._localized(reason.get('text')))}")
        player = self._t("黑棋", "Black") if result.get("player") == "B" else self._t("白棋", "White")
        heading(self._t("同一局面的候选比较", "Candidates in the same position") + " · " + player + self._t("视角", " perspective"))
        for candidate in [result.get("selected"), result.get("alternative")]:
            if candidate:
                sections.append(escape_markup(f"{candidate.get('move')} · {self._t('胜率', 'winrate')} {candidate['winrate']:.1f}% · {self._t('目差', 'lead')} {candidate['score_lead']:+.1f} · {candidate.get('visits', 0)} {self._t('次搜索', 'visits')}"))
        difference = result.get("comparison")
        if difference:
            sections.append(escape_markup(self._t("所选着法相对替代着法：", "Chosen versus alternative: ") + f"{difference['winrate_pp']:+.1f} " + self._t("个百分点。", "percentage points.")))
        sections.append(escape_markup(self._t("候选优势与沿变化的评估波动分别展示；一选并不保证胜率上升。", "Candidate advantage and evaluation drift along a line are shown separately. The first choice does not guarantee a winrate increase.")))
        heading(self._t("讲解着法的后续演变", "Selected move continuation"))
        for note in explanation.get("continuation", []):
            sections.append(escape_markup(self._localized(note)))
        heading(self._t("逐手评估", "Evaluations along the line"))
        previous = None
        for step in self._branch().get("steps", []):
            metric = step.get("eval")
            if not metric:
                continue
            delta = "—" if previous is None else f"{metric['winrate'] - previous:+.1f} pp"
            sections.append(escape_markup(f"{step.get('ply', 0)} · {step.get('move') or self._t('起始', 'start')} · {metric['winrate']:.1f}% · Δ {delta} · {metric['score_lead']:+.1f} {self._t('目', 'points')}"))
            previous = metric["winrate"]
        heading(self._t("解释的边界", "Limits of this explanation"))
        for note in list(explanation.get("limitations", [])) + list(result.get("warnings", [])):
            sections.append("• " + escape_markup(self._localized(note)))
        self._report.text = "\n\n".join(sections)


Factory.register("KaTrainExplainerPanel", cls=KaTrainExplainerPanel)
