"""The plugin's look and feel for KaTrain 1.20, plus faster stone placement.

Imported from the top of the patched ``gui.kv``, before KaTrain builds its
window, so the colours and textures below are what the interface is built
with. Everything here is applied at run time to KaTrain's own classes; no
KaTrain file other than ``gui.kv`` is changed, and uninstalling the plugin
restores the original interface.

Depth comes from three things: a wooden board drawn as a slab with a side
face and a cast shadow, stones rendered with a highlight and a contact shadow
(baked into the textures in this folder), and panels and buttons drawn as
raised or sunken surfaces by the ``<BackgroundMixin>`` rule in ``gui.kv``.
"""

from __future__ import annotations

import time
from pathlib import Path

from kivy.clock import Clock
from kivy.graphics import BorderImage, Color, Line, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.resources import resource_add_path

from katrain.gui.theme import Theme

# Shadows are one small pre-blurred image stretched as a nine-patch. A blur
# shader looks the same but is recomputed every frame, which made the whole
# window several times slower to redraw on a software renderer.
SHADOW_BORDER = 40  # px in kx_shadow.png; must match scripts/build_skin_assets.py


# ---------------------------------------------------------------- palette

TABLE_TOP = [0.285, 0.325, 0.385, 1]      # window background, upper edge
TABLE_BOTTOM = [0.135, 0.160, 0.200, 1]   # window background, lower edge
BAR = [0.190, 0.222, 0.270, 1]            # toolbars above and below the board
SURFACE = [0.205, 0.240, 0.292, 1]        # raised cards
SURFACE_HIGH = [0.270, 0.312, 0.376, 1]   # the card or key that is active
SUNKEN = [0.075, 0.090, 0.116, 1]         # wells: clock, graph, text areas
BUTTON = [0.300, 0.346, 0.415, 1]         # raised keys
ACCENT = [0.980, 0.760, 0.290, 1]         # amber: the current mode and player
ACTION = [0.250, 0.640, 0.450, 1]         # green: the explanation buttons
EDGE = [1, 1, 1, 0.07]                    # hairline on raised surfaces
TEXT_DIM = [0.70, 0.75, 0.81, 1]

_installed = False
_gradients = {}


def gradient(top, bottom, steps=64):
    """A vertical colour ramp as a texture, for surfaces that are lit from above."""
    key = (tuple(top), tuple(bottom), steps)
    if key not in _gradients:
        texture = Texture.create(size=(1, steps), colorfmt="rgba")
        data = bytearray()
        for index in range(steps):  # row 0 is the bottom of the texture
            mix = index / (steps - 1)
            for low, high in zip(bottom, top):
                data.append(max(0, min(255, int(round(255 * (low + (high - low) * mix))))))
        texture.blit_buffer(bytes(data), colorfmt="rgba", bufferfmt="ubyte")
        texture.mag_filter = texture.min_filter = "linear"
        _gradients[key] = texture
    return _gradients[key]


def gloss():
    """Light falling on a raised surface: brighter at the top, shaded at the bottom."""
    key = "gloss"
    if key not in _gradients:
        steps = 64
        texture = Texture.create(size=(1, steps), colorfmt="rgba")
        data = bytearray()
        for index in range(steps):
            mix = index / (steps - 1)  # 0 bottom, 1 top
            if mix > 0.5:
                data.extend((255, 255, 255, int(255 * 0.11 * ((mix - 0.5) * 2) ** 1.3)))
            else:
                data.extend((0, 0, 0, int(255 * 0.16 * ((0.5 - mix) * 2) ** 1.3)))
        texture.blit_buffer(bytes(data), colorfmt="rgba", bufferfmt="ubyte")
        texture.mag_filter = texture.min_filter = "linear"
        _gradients[key] = texture
    return _gradients[key]


def table():
    return gradient(TABLE_TOP, TABLE_BOTTOM)


def inset():
    """Shade inside the top edge of a well, with a faint light on its lower lip."""
    key = "inset"
    if key not in _gradients:
        steps = 64
        texture = Texture.create(size=(1, steps), colorfmt="rgba")
        data = bytearray()
        for index in range(steps):
            mix = index / (steps - 1)  # 0 bottom, 1 top
            if mix > 0.62:
                data.extend((0, 0, 0, int(255 * 0.55 * ((mix - 0.62) / 0.38) ** 1.6)))
            elif mix < 0.06:
                data.extend((255, 255, 255, int(255 * 0.07 * (1 - mix / 0.06))))
            else:
                data.extend((0, 0, 0, 0))
        texture.blit_buffer(bytes(data), colorfmt="rgba", bufferfmt="ubyte")
        texture.mag_filter = texture.min_filter = "linear"
        _gradients[key] = texture
    return _gradients[key]


def shadow():
    """The nine-patch drop shadow texture."""
    return image("kx_shadow.png")


def drop_shadow(x, y, width, height, spread, offset, alpha):
    """Draw a drop shadow for a rectangle on the current canvas; returns (Color, BorderImage)."""
    texture = shadow()
    color = Color(0, 0, 0, alpha if texture is not None else 0)
    patch = BorderImage(texture=texture, border=(SHADOW_BORDER,) * 4, display_border=(max(1, spread),) * 4,
                        pos=(x - spread, y - spread - offset), size=(width + 2 * spread, height + 2 * spread))
    return color, patch


def place_shadow(patch, x, y, width, height, spread, offset):
    patch.display_border = (max(1, spread),) * 4
    patch.pos, patch.size = (x - spread, y - spread - offset), (width + 2 * spread, height + 2 * spread)


_images = {}


def image(name):
    """Texture of one of the skin's image files (board and stones), or None if it cannot be loaded."""
    if name not in _images:
        try:
            from kivy.core.image import Image as CoreImage
            from kivy.resources import resource_find

            _images[name] = CoreImage(resource_find(name) or str(Path(__file__).with_name(name))).texture
        except Exception:
            _images[name] = None
    return _images[name]


def lighter(color, amount=0.08):
    return [min(1.0, channel + amount) for channel in color[:3]] + [color[3] if len(color) > 3 else 1]


def darker(color, amount=0.08):
    return [max(0.0, channel - amount) for channel in color[:3]] + [color[3] if len(color) > 3 else 1]


def _replace(owner, name, function):
    """Install `function` as `owner.name`.

    Kivy's clock keeps weak references to bound methods and finds them again by
    ``__name__``, so a replacement must carry the name it is installed under.
    """
    function.__name__ = name
    function.__qualname__ = f"{owner.__name__}.{name}"
    setattr(owner, name, function)


# ------------------------------------------------------------------ theme

def _apply_theme():
    Theme.BACKGROUND_COLOR = [0.130, 0.152, 0.190, 1]
    Theme.BOX_BACKGROUND_COLOR = SURFACE
    Theme.LIGHTER_BACKGROUND_COLOR = SURFACE_HIGH
    Theme.PLAY_ANALYZE_TAB_COLOR = ACCENT
    Theme.BUTTON_INACTIVE_COLOR = [0.56, 0.61, 0.68, 1]
    Theme.BUTTON_BORDER_COLOR = [0.93, 0.95, 0.97, 1]
    Theme.SCROLLBAR_COLOR = [0.62, 0.67, 0.74, 0.9]
    Theme.REGION_BORDER_COLOR = SURFACE_HIGH
    Theme.BOARD_TEXTURE = "kx_board.png"
    Theme.STONE_TEXTURE = {"B": "kx_stone_b.png", "W": "kx_stone_w.png"}
    Theme.STONE_SIZE = 0.555  # the stone fills 88% of its texture; the rest is its shadow
    Theme.LINE_COLOR = [0.17, 0.11, 0.05, 0.92]
    Theme.STARPOINT_SIZE = 0.11
    Theme.APPROX_BOARD_COLOR = [0.87, 0.67, 0.38, 1]
    Theme.BOARD_COLOR = [0.87, 0.67, 0.38, 1]
    Theme.NUMBER_COLOR = [0.93, 0.74, 0.42, 0.9]
    Theme.GHOST_ALPHA = 0.55


# ------------------------------------------------------------------ board

BOARD_SCALE = 0.955   # leaves room for the slab's side face and shadow
SLAB_DEPTH = 0.34     # side face height, in grid units
COORDINATE_COLOR = (0.30, 0.19, 0.08)


def _patch_board(badukpan):
    board_class = badukpan.BadukPanWidget
    cached_texture = badukpan.cached_texture
    original_grid_size = board_class.calculate_grid_size
    original_coordinates = board_class.draw_coordinates

    def calculate_grid_size(self, width, height, x_grid_spaces, y_grid_spaces):
        # KaTrain keeps the grid size integral so shaded squares meet without gaps.
        return max(1, int(original_grid_size(self, width, height, x_grid_spaces, y_grid_spaces) * BOARD_SCALE))

    def draw_board_background(self, katrain, gridpos_x, gridpos_y, x_grid_spaces, y_grid_spaces,
                              grid_spaces_margin_x, grid_spaces_margin_y):
        grid = self.grid_size
        left = gridpos_x[0] - grid * grid_spaces_margin_x[0]
        bottom = gridpos_y[0] - grid * grid_spaces_margin_y[0]
        width, height = grid * x_grid_spaces, grid * y_grid_spaces
        depth = grid * SLAB_DEPTH
        radius = grid * 0.16
        wood = cached_texture(Theme.BOARD_TEXTURE)
        tint = Theme.INSERT_BOARD_COLOR_TINT if katrain.game.insert_mode else Theme.BOARD_COLOR_TINT
        # cast shadow on the table, offset down as if lit from above
        drop_shadow(left, bottom - depth, width, height + depth, spread=grid * 1.0, offset=grid * 0.34, alpha=0.85)
        # side face: the same wood, in shade
        Color(0.50 * tint[0], 0.42 * tint[1], 0.34 * tint[2], tint[3])
        RoundedRectangle(pos=(left, bottom - depth), size=(width, height * 0.5 + depth),
                         radius=[(radius, radius)] * 4, texture=wood)
        Color(0, 0, 0, 0.30)
        Line(points=[left + radius, bottom - depth, left + width - radius, bottom - depth], width=1)
        # top face
        Color(*tint)
        RoundedRectangle(pos=(left, bottom), size=(width, height), radius=[(radius, radius)] * 4, texture=wood)
        # bevel: light catches the upper and left edges, the lower and right ones fall away
        Color(1, 0.96, 0.86, 0.50)
        Line(points=[left + radius, bottom + height - 1, left + width - radius, bottom + height - 1], width=1.1)
        Color(1, 0.96, 0.86, 0.22)
        Line(points=[left + 1, bottom + radius, left + 1, bottom + height - radius], width=1.1)
        Color(0.20, 0.11, 0.03, 0.40)
        Line(points=[left + radius, bottom + 0.5, left + width - radius, bottom + 0.5], width=1.2)
        Color(0.20, 0.11, 0.03, 0.22)
        Line(points=[left + width - 1, bottom + radius, left + width - 1, bottom + height - radius], width=1.1)
        # a thin frame just outside the grid, as on a real board
        Color(*Theme.LINE_COLOR[:3], 0.9)
        Line(rectangle=(gridpos_x[0], gridpos_y[0], gridpos_x[-1] - gridpos_x[0], gridpos_y[-1] - gridpos_y[0]),
             width=1.6)

    def draw_coordinates(self, gridpos_x, gridpos_y):
        # KaTrain draws its coordinates in neutral grey; keep them in the wood's own dark tone.
        original_color = badukpan.Color

        def color(*args, **kwargs):
            if len(args) == 3 and all(abs(value - 0.25) < 1e-6 for value in args):
                return original_color(*COORDINATE_COLOR, **kwargs)
            return original_color(*args, **kwargs)

        badukpan.Color = color
        try:
            return original_coordinates(self, gridpos_x, gridpos_y)
        finally:
            badukpan.Color = original_color

    _replace(board_class, "calculate_grid_size", calculate_grid_size)
    _replace(board_class, "draw_board_background", draw_board_background)
    _replace(board_class, "draw_coordinates", draw_coordinates)


# --------------------------------------------------------- stone placement

PENDING_SECONDS = 1.5


def _patch_placement(badukpan, main):
    """Show a played stone on the frame after the click.

    KaTrain hands a click to a worker thread, which plays the move, starts the
    analysis and then asks the interface to redraw; the board itself redraws
    0.05 s after that. Until then the ghost stone has already vanished, so the
    point is empty for a moment. Here the stone is drawn at once in the overlay
    layer and removed when the real board catches up; redraw requests are also
    served on the next frame, and repeated state refreshes are merged so a click
    never waits behind a queue of them.
    """
    board_class = badukpan.BadukPanWidget
    gui_class = main.KaTrainGui
    original_init = board_class.__init__
    original_touch_up = board_class.on_touch_up
    original_hover = board_class.draw_hover_contents
    original_contents = board_class.draw_board_contents
    original_call = gui_class.__call__
    original_stone_sound = gui_class._play_stone_sound
    original_do_play = gui_class._do_play

    def init(self, **kwargs):
        original_init(self, **kwargs)
        self.kx_pending = None
        self.redraw_board_contents_trigger = Clock.create_trigger(self.draw_board_contents, 0)
        self.redraw_hover_contents_trigger = Clock.create_trigger(self.draw_hover_contents, 0)

    def call(self, message, *args, **kwargs):
        if message == "play" and args and args[0] is not None:
            self.kx_last_play = (tuple(args[0]), time.perf_counter())
        elif message == "update_state" and not args and not kwargs.get("redraw_board"):
            # Every pending refresh does the same work, so one in the queue is enough.
            now = time.perf_counter()
            if now - getattr(self, "kx_refresh_queued_at", 0) < 0.2:
                return None  # a refresh queued a moment ago has not run yet
            self.kx_refresh_queued_at = now
        return original_call(self, message, *args, **kwargs)

    original_update = gui_class._do_update_state

    def do_update_state(self, *args, **kwargs):
        self.kx_refresh_queued_at = 0
        return original_update(self, *args, **kwargs)

    def touch_up(self, touch):
        katrain = self.katrain
        before = getattr(katrain, "kx_last_play", None)
        released = time.perf_counter()
        try:
            player = katrain.next_player_info.player if katrain and katrain.game else None
        except Exception:
            player = None
        result = original_touch_up(self, touch)
        after = getattr(katrain, "kx_last_play", None)
        if player and after is not None and after is not before:
            self.kx_pending = (after[0], player, released, katrain.game.current_node)
            try:  # the sound belongs to the click, not to the worker thread's schedule
                katrain.kx_sound_at = released
                if not katrain.game.current_node.children:  # a new move, not a step along a variation
                    original_stone_sound(katrain)
                else:
                    katrain.kx_sound_at = 0
            except Exception:
                pass
            self.draw_hover_contents()
        return result

    def stone_sound(self, _dt=None):
        if time.perf_counter() - getattr(self, "kx_sound_at", 0) < 0.6:
            self.kx_sound_at = 0  # only this move's own sound is skipped, not the reply's
            return None
        return original_stone_sound(self, _dt)

    def do_play(self, coords):
        result = original_do_play(self, coords)
        board = getattr(self, "board_gui", None)
        pending = getattr(board, "kx_pending", None) if board else None
        if pending and coords is not None and tuple(coords) == pending[0]:
            node = self.game.current_node
            played = node.move and tuple(node.move.coords) == pending[0] and node is not pending[3]
            if not played:  # illegal move: take the stone back at once
                board.kx_pending = None
                board.redraw_hover_contents_trigger()
        return result

    def draw_hover(self, *args):
        original_hover(self, *args)
        pending = getattr(self, "kx_pending", None)
        if not pending:
            return
        coords, player, started, _node = pending
        if time.perf_counter() - started > PENDING_SECONDS:
            self.kx_pending = None
            return
        try:
            with self.canvas.after:
                self.draw_stone(coords[0], coords[1], player)
        except Exception:
            self.kx_pending = None

    def draw_contents(self, *args):
        original_contents(self, *args)
        pending = getattr(self, "kx_pending", None)
        if not pending:
            return
        coords, _player, started, node = pending
        game = self.katrain.game if self.katrain else None
        current = game.current_node if game else None
        if current is not None and current is not node:
            # The real board now shows the move (or the game moved on): drop the stand-in.
            self.kx_pending = None
            self.draw_hover_contents()

    _replace(board_class, "__init__", init)
    _replace(board_class, "on_touch_up", touch_up)
    _replace(board_class, "draw_hover_contents", draw_hover)
    _replace(board_class, "draw_board_contents", draw_contents)
    _replace(gui_class, "__call__", call)
    _replace(gui_class, "_do_update_state", do_update_state)
    _replace(gui_class, "_play_stone_sound", stone_sound)
    _replace(gui_class, "_do_play", do_play)


# ---------------------------------------------------------------- install

def install():
    """Apply the skin once. Safe to call again; failures leave KaTrain's own look."""
    global _installed
    if _installed:
        return True
    _installed = True
    resource_add_path(str(Path(__file__).resolve().parent))
    _apply_theme()
    try:
        import katrain.gui.badukpan as badukpan

        _patch_board(badukpan)
    except Exception as error:  # pragma: no cover - never stop KaTrain from opening
        print("KataGoExplainer: board skin not applied:", error)
    try:
        import sys

        main = sys.modules.get("katrain.__main__") or sys.modules.get("__main__")
        import katrain.gui.badukpan as badukpan

        if main is not None and hasattr(main, "KaTrainGui"):
            _patch_placement(badukpan, main)
    except Exception as error:  # pragma: no cover
        print("KataGoExplainer: fast placement not applied:", error)
    return True


install()
