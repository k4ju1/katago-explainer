"""Ask a large language model about the game, inside KaTrain.

A sheet on the right-hand side of the window: the board stays visible while
the conversation runs. Each question is sent together with the current
position, KataGo's numbers for it and the explanation already generated for
this move, so the answer is about this game rather than Go in general.
"""
from __future__ import annotations

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, InstructionGroup, Line, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from katrain.gui.theme import Theme

from . import chat_context as core
from . import skin
from .llm import PRESETS
from .panel import (Card, ClickCard, GREEN, GREEN_DEEP, KEY, MUTED, PANEL, VERDICT_COLORS, KeyButton, _SCALE,
                    _flow, _wrap_label, ds, fs, viewer_scale)

USER_TINT = (0.980, 0.760, 0.290, 1)
STREAM_INTERVAL = 0.06


class Field(TextInput):
    """A text box drawn as a well, in KaTrain's font so Chinese input displays."""

    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", Theme.DEFAULT_FONT)
        kwargs.setdefault("font_size", fs(14))
        kwargs.setdefault("multiline", False)
        kwargs.setdefault("write_tab", False)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_active", "")
        kwargs.setdefault("background_disabled_normal", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("foreground_color", Theme.TEXT_COLOR)
        kwargs.setdefault("disabled_foreground_color", MUTED)
        kwargs.setdefault("hint_text_color", (0.55, 0.60, 0.67, 1))
        kwargs.setdefault("cursor_color", USER_TINT)
        kwargs.setdefault("selection_color", (0.98, 0.76, 0.29, 0.35))
        kwargs.setdefault("padding", (ds(12), ds(9), ds(12), ds(8)))
        super().__init__(**kwargs)
        # Drawn underneath TextInput's own instructions: the colour it sets for the text must stay last.
        well = InstructionGroup()
        well.add(Color(*skin.SUNKEN))
        self._well = RoundedRectangle(radius=[ds(9)])
        well.add(self._well)
        well.add(Color(1, 1, 1, 1))
        self._shade = RoundedRectangle(radius=[ds(9)], texture=skin.inset())
        well.add(self._shade)
        self._ring_color = Color(*skin.EDGE)
        well.add(self._ring_color)
        self._ring = Line(width=1.1)
        well.add(self._ring)
        self.canvas.before.insert(0, well)
        self.bind(pos=self._sync, size=self._sync, focus=self._sync)

    def _sync(self, *_args):
        for shape in (self._well, self._shade):
            shape.pos, shape.size = self.pos, self.size
        self._ring_color.rgba = USER_TINT if self.focus else skin.EDGE
        self._ring.rounded_rectangle = (self.x, self.y, self.width, self.height, ds(9))


class ChatSheet:
    """Owns the popup, the conversation and the settings form."""

    def __init__(self, panel):
        self.panel = panel
        self.session = core.ChatSession()
        self.settings_file = core.settings_path(getattr(panel.katrain, "config_file", None))
        self.settings = core.load_settings(self.settings_file)
        self._popup = None
        self._mode = "chat"
        self._pending = []
        self._live = None       # the label of the reply being written
        self._live_text = ""
        self._flush_event = None
        self._test_session = None

    # ----------------------------------------------------------------- helpers
    def _t(self, zh, en):
        return self.panel._t(zh, en)

    @property
    def language(self):
        return "zh" if self.panel._language == "zh" else "en"

    def _button(self, text, callback, **kwargs):
        kwargs.setdefault("font_size", fs(12))
        button = KeyButton(text=text, **kwargs)
        button.bind(on_release=callback)
        return button

    def _label(self, text, size=13, color=None, height=None, halign="left"):
        label = Label(text=text, font_name=Theme.DEFAULT_FONT, font_size=fs(size), color=color or Theme.TEXT_COLOR,
                      halign=halign, valign="middle", shorten=True, shorten_from="right")
        label.bind(size=lambda widget, size_: setattr(widget, "text_size", size_))
        if height is not None:
            label.size_hint_y, label.height = None, ds(height)
        return label

    # ------------------------------------------------------------------- build
    def open(self, question=None):
        scale = viewer_scale(Window.height)
        if self._popup is None or abs(scale - _SCALE[0]) >= 0.08:
            if self._popup is not None:
                self._popup.dismiss()
            if self.panel._popup is None:
                _SCALE[0] = scale
            self._build()
        self._mode = "chat" if core.is_configured(self.settings) else "settings"
        self._popup.open()
        self._refresh()
        if question:
            self.send(question)
        elif self._mode == "chat":
            Clock.schedule_once(lambda _dt: setattr(self._input, "focus", True), 0.15)

    def _build(self):
        content = BoxLayout(orientation="vertical", spacing=ds(8), padding=(ds(6), ds(4), ds(6), ds(6)))
        header = BoxLayout(size_hint_y=None, height=ds(36), spacing=ds(6))
        self._title = self._label("", 16)
        header.add_widget(self._title)
        self._settings_button = self._button("", self._toggle_settings, size_hint_x=None, width=ds(72))
        self._clear_button = self._button("", self._clear, size_hint_x=None, width=ds(72))
        self._close_button = self._button("", lambda *_: self._popup.dismiss(), size_hint_x=None, width=ds(64))
        for button in (self._settings_button, self._clear_button, self._close_button):
            header.add_widget(button)
        content.add_widget(header)
        self._context_label = self._label("", 11, MUTED, height=16)
        content.add_widget(self._context_label)
        self._body = BoxLayout(orientation="vertical", spacing=ds(8))
        content.add_widget(self._body)

        # conversation
        self._chat_box = BoxLayout(orientation="vertical", spacing=ds(8))
        self._scroll = ScrollView(do_scroll_x=False, bar_width=ds(5), scroll_type=["bars", "content"])
        self._messages = GridLayout(cols=1, size_hint_y=None, spacing=ds(8), padding=(0, 0, ds(8), ds(6)))
        self._messages.bind(minimum_height=self._messages.setter("height"))
        self._scroll.add_widget(self._messages)
        self._chat_box.add_widget(self._scroll)
        entry = BoxLayout(size_hint_y=None, height=ds(40), spacing=ds(6))
        self._input = Field()
        self._input.bind(on_text_validate=lambda *_: self.send(self._input.text))
        entry.add_widget(self._input)
        self._send_button = self._button("", self._send_or_stop, size_hint_x=None, width=ds(76),
                                         background_color=list(GREEN_DEEP), font_size=fs(13))
        entry.add_widget(self._send_button)
        self._chat_box.add_widget(entry)

        # settings
        self._form = self._build_form()

        width = min(Window.width * 0.92, max(ds(400), Window.width * 0.36))
        self._popup = Popup(title="", title_font=Theme.DEFAULT_FONT, title_size=fs(13), title_color=MUTED,
                            content=content, size_hint=(None, 0.94), width=width,
                            pos_hint={"right": 0.992, "center_y": 0.5}, auto_dismiss=True,
                            separator_color=USER_TINT, separator_height=ds(1),
                            background="", background_color=PANEL, overlay_color=(0, 0, 0, 0.28))
        self._popup.bind(on_dismiss=self._on_dismiss)

    def _build_form(self):
        scroll = ScrollView(do_scroll_x=False, bar_width=ds(5), scroll_type=["bars", "content"])
        form = GridLayout(cols=1, size_hint_y=None, spacing=ds(8), padding=(0, 0, ds(8), ds(6)))
        form.bind(minimum_height=form.setter("height"))
        self._form_note = _wrap_label("", fs(12), MUTED)
        form.add_widget(self._form_note)
        self._preset_caption = self._label("", 12, MUTED, height=18)
        form.add_widget(self._preset_caption)
        presets = GridLayout(cols=2, size_hint_y=None, spacing=ds(6), row_default_height=ds(32), row_force_default=True)
        presets.bind(minimum_height=presets.setter("height"))
        self._preset_buttons = {}
        for name, _protocol, _base, _model in PRESETS:
            button = self._button(name, lambda _button, chosen=name: self._choose_preset(chosen))
            self._preset_buttons[name] = button
            presets.add_widget(button)
        form.add_widget(presets)
        self._field_captions, self._fields = {}, {}
        for key in ("base_url", "model", "api_key"):
            caption = self._label("", 12, MUTED, height=18)
            field = Field(size_hint_y=None, height=ds(38), password=(key == "api_key"))
            self._field_captions[key], self._fields[key] = caption, field
            form.add_widget(caption)
            form.add_widget(field)
        self._privacy = _wrap_label("", fs(11), MUTED)
        form.add_widget(self._privacy)
        actions = BoxLayout(size_hint_y=None, height=ds(36), spacing=ds(6))
        self._save_button = self._button("", self._save, background_color=list(GREEN_DEEP), font_size=fs(13))
        self._test_button = self._button("", self._test, font_size=fs(13))
        actions.add_widget(self._save_button)
        actions.add_widget(self._test_button)
        form.add_widget(actions)
        self._form_status = _wrap_label("", fs(12), MUTED)
        form.add_widget(self._form_status)
        scroll.add_widget(form)
        return scroll

    # ----------------------------------------------------------------- refresh
    def _refresh(self):
        if self._popup is None:
            return
        self._popup.title = self._t("问 AI · 大模型问答", "Ask AI · language model")
        self._close_button.text = self._t("关闭", "Close")
        self._clear_button.text = self._t("清空", "Clear")
        self._settings_button.text = self._t("返回", "Back") if self._mode == "settings" else self._t("设置", "Settings")
        self._clear_button.disabled = self._mode == "settings" or not self.session.messages
        self._body.clear_widgets()
        if self._mode == "settings":
            self._title.text = self._t("连接大模型", "Connect a model")
            self._context_label.text = ""
            self._fill_form()
            self._body.add_widget(self._form)
            return
        self._title.text = self._position_title()
        self._context_label.text = self._context_summary()
        self._input.hint_text = self._t("就当前局面提问，回车发送", "Ask about this position, Enter to send")
        self._sync_send()
        self._body.add_widget(self._chat_box)
        self._render_messages()

    def _game(self):
        gui = self.panel.katrain
        return getattr(gui, "game", None) if gui is not None else None

    def _position_title(self):
        game = self._game()
        try:
            node = game.current_node
            moves = [move for item in node.nodes_from_root for move in item.moves]
            if not moves:
                return self._t("开局 · 尚未落子", "Empty board")
            last = moves[-1]
            side = self._t("黑", "Black") if last.player == "B" else self._t("白", "White")
            return self._t(f"第 {len(moves)} 手 · {side} {last.gtp()}", f"Move {len(moves)} · {side} {last.gtp()}")
        except Exception:
            return self._t("当前局面", "Current position")

    def _current_explanation(self):
        result, bridge = self.panel._result, self.panel._bridge
        try:
            if result and not self.panel._error and bridge is not None and bridge.is_current(result):
                return result
        except Exception:
            pass
        return None

    def _context_summary(self):
        parts = [self._t("棋谱与局面", "moves and position")]
        game = self._game()
        try:
            node = game.current_node
            if node.analysis_exists:
                parts.append(self._t(f"KataGo 分析（{node.root_visits} 次搜索）", f"KataGo analysis ({node.root_visits} visits)"))
            else:
                parts.append(self._t("KataGo 尚未分析完", "KataGo still analysing"))
        except Exception:
            pass
        if self._current_explanation():
            parts.append(self._t("本手讲解", "this move's explanation"))
        model = str(self.settings.get("model") or "")
        return self._t("AI 能看到：", "The model sees: ") + " · ".join(parts) + (f"   ·   {model}" if model else "")

    def _sync_send(self):
        busy = self.session.busy
        self._send_button.text = self._t("停止", "Stop") if busy else self._t("发送", "Send")
        self._send_button.background_color = list(KEY) if busy else list(GREEN_DEEP)
        self._input.disabled = False

    # ---------------------------------------------------------------- messages
    def _bubble(self, role, text, note=None):
        user = role == "user"
        card = Card(accent=USER_TINT if user else GREEN, background=tuple(skin.SURFACE_HIGH) if user else tuple(skin.SURFACE),
                    elevation=0.35)
        tag = self._t("你", "You") if user else (note or "AI")
        head = self._label(tag, 11, USER_TINT if user else GREEN, height=15)
        head.bold = True
        card.add_widget(head)
        body = _wrap_label("", fs(14))
        body.markup = True
        body.text = _flow(core.to_markup(text)) if text else ""
        card.add_widget(body)
        self._messages.add_widget(card)
        return body

    def _notice(self, text, color=MUTED):
        card = Card(accent=color, elevation=0.2)
        card.add_widget(_wrap_label(text, fs(13), color))
        self._messages.add_widget(card)

    def _render_messages(self):
        self._messages.clear_widgets()
        self._live = None
        if not self.session.messages:
            self._messages.add_widget(_wrap_label(self._t(
                "可以直接问这盘棋：AI 会结合当前局面、KataGo 的搜索结果和已生成的讲解来回答。",
                "Ask anything about this game: the answer uses the current position, KataGo's search and the explanation already generated."),
                fs(13), MUTED))
            for prompt in core.QUICK_PROMPTS[self.language]:
                card = ClickCard(elevation=0.35, padding=(ds(14), ds(9), ds(12), ds(10)))
                card.add_widget(_wrap_label(prompt, fs(14)))
                card.bind(on_release=lambda _card, text=prompt: self.send(text))
                self._messages.add_widget(card)
            return
        for message in self.session.messages:
            self._bubble(message["role"], message["content"])
        if self.session.busy:
            self._live = self._bubble("assistant", self._live_text or "…")
        self._scroll_to_end()

    def _scroll_to_end(self):
        Clock.schedule_once(lambda _dt: setattr(self._scroll, "scroll_y", 0), 0.05)

    # -------------------------------------------------------------------- send
    def _send_or_stop(self, *_args):
        if self.session.busy:
            self.session.stop()
            if self._live_text:
                self.session.messages.append({"role": "assistant", "content": self._live_text})
            self._live_text = ""
            self._refresh()
        else:
            self.send(self._input.text)

    def send(self, text):
        text = str(text or "").strip()
        if not text or self.session.busy:
            return
        if not core.is_configured(self.settings):
            self._mode = "settings"
            self._refresh()
            self._form_status.color = VERDICT_COLORS["inaccuracy"]
            self._form_status.text = self._t("先选择一个大模型服务并填写 API Key。", "Choose a model service and enter its API key first.")
            return
        game = self._game()
        try:
            lock = getattr(game, "_lock", None)
            if lock is not None:
                with lock:
                    game_text = core.game_context(game, self.language)
            else:
                game_text = core.game_context(game, self.language)
        except Exception as error:
            game_text = self._t(f"（读取棋局失败：{error}）", f"(Could not read the game: {error})")
        system = core.build_system(game_text, core.explanation_context(self._current_explanation(), self.language),
                                   self.language)
        self._live_text = ""
        started = self.session.ask(
            text, self.settings, system,
            on_delta=self._on_delta,
            on_done=lambda reply: Clock.schedule_once(lambda _dt: self._on_done(), 0),
            on_error=lambda message: Clock.schedule_once(lambda _dt: self._on_error(message), 0))
        if started:
            self._input.text = ""
            self._refresh()
            Clock.schedule_once(lambda _dt: setattr(self._input, "focus", True), 0.1)

    def _on_delta(self, piece):
        # Worker thread: collect, and let the interface thread draw at a steady pace.
        self._pending.append(piece)
        if self._flush_event is None:
            self._flush_event = Clock.schedule_once(self._flush, STREAM_INTERVAL)

    def _flush(self, _dt=None):
        self._flush_event = None
        pieces, self._pending = self._pending, []
        if not pieces or not self.session.busy:
            return
        self._live_text += "".join(pieces)
        if self._live is not None and self._mode == "chat":
            near_end = self._scroll.scroll_y < 0.03 or self._messages.height <= self._scroll.height
            self._live.text = _flow(core.to_markup(self._live_text))
            if near_end:
                self._scroll_to_end()

    def _on_done(self):
        self._pending, self._live_text = [], ""
        if self._popup is not None:
            self._refresh()

    def _on_error(self, message):
        self._pending, self._live_text = [], ""
        if self._popup is None:
            return
        self._refresh()
        if self._mode == "chat":
            self._notice(message, VERDICT_COLORS["mistake"])
            self._scroll_to_end()

    def _clear(self, *_args):
        self.session.clear()
        self._live_text = ""
        self._refresh()

    def _on_dismiss(self, *_args):
        self._input.focus = False
        for field in self._fields.values():
            field.focus = False

    # ---------------------------------------------------------------- settings
    def _toggle_settings(self, *_args):
        self._mode = "chat" if self._mode == "settings" else "settings"
        self._refresh()

    def _fill_form(self):
        self._form_note.text = _flow(self._t(
            "选择一个大模型服务，填入你自己的 API Key。国内外的 OpenAI 兼容接口和 Claude 接口都可以用；本机的 Ollama 不需要 Key。",
            "Choose a model service and enter your own API key. OpenAI-compatible services and the Claude API both work; a local Ollama needs no key."))
        self._preset_caption.text = self._t("服务商", "Service")
        captions = {"base_url": self._t("接口地址", "Base URL"), "model": self._t("模型名称", "Model"),
                    "api_key": "API Key"}
        for key, caption in self._field_captions.items():
            caption.text = captions[key]
            self._fields[key].text = str(self.settings.get(key) or "")
        self._privacy.text = _flow(self._t(
            f"Key 只保存在这台电脑上（{self.settings_file}）。提问时，棋谱、当前局面和 KataGo 的分析数据会发送给你选择的服务商。",
            f"The key is stored only on this computer ({self.settings_file}). Each question sends the moves, the position and KataGo's analysis to the service you choose."))
        self._save_button.text = self._t("保存", "Save")
        self._test_button.text = self._t("测试连接", "Test connection")
        self._form_status.text = ""
        self._mark_preset()

    def _mark_preset(self):
        for name, button in self._preset_buttons.items():
            button.background_color = list(GREEN_DEEP) if name == self.settings.get("preset") else list(KEY)

    def _choose_preset(self, name):
        for preset, protocol, base_url, model in PRESETS:
            if preset == name:
                self.settings.update({"preset": preset, "protocol": protocol})
                self._fields["base_url"].text, self._fields["model"].text = base_url, model
        self._mark_preset()

    def _read_form(self):
        for key, field in self._fields.items():
            self.settings[key] = field.text.strip()
        return self.settings

    def _save(self, *_args):
        self._read_form()
        try:
            core.save_settings(self.settings, self.settings_file)
        except OSError as error:
            self._form_status.color = VERDICT_COLORS["mistake"]
            self._form_status.text = self._t(f"保存失败：{error}", f"Could not save: {error}")
            return
        if core.is_configured(self.settings):
            self._mode = "chat"
            self._refresh()
        else:
            self._form_status.color = VERDICT_COLORS["inaccuracy"]
            self._form_status.text = self._t("已保存，但还缺少接口地址、模型或 API Key。", "Saved, but the URL, model or API key is still missing.")

    def _test(self, *_args):
        self._read_form()
        self._form_status.color = MUTED
        self._form_status.text = self._t("正在连接…", "Connecting…")
        session = self._test_session = core.ChatSession()

        def show(text, color):
            def apply(_dt):
                if self._test_session is session:
                    self._form_status.color, self._form_status.text = color, _flow(text)
            Clock.schedule_once(apply, 0)

        session.ask(self._t("请只回复“连接成功”。", "Reply with just: connected."), dict(self.settings, max_tokens=30),
                    self._t("你是连接测试助手。", "You are a connection test."),
                    on_delta=lambda piece: None,
                    on_done=lambda reply: show(self._t("连接成功，模型回复：", "Connected. The model replied: ") + reply.strip()[:60], GREEN),
                    on_error=lambda message: show(message, VERDICT_COLORS["mistake"]))
