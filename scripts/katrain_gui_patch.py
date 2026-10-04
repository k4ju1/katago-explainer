"""The plugin's changes to KaTrain v1.20.0's ``gui.kv``, as exact replacements.

Each entry replaces one piece of the original file. Applying them to anything
other than the pinned original fails loudly instead of producing a half-styled
interface. Widget ids and the widget tree are kept as KaTrain's code expects;
only drawing, sizes and colours change, and the explanation dock is added.
"""

MARKER = '# KataGo Explainer native integration v2'

IMPORTS = '''#:import kx katrain_explainer.skin
#:import KaTrainExplainerPanel katrain_explainer.panel.KaTrainExplainerPanel
'''

REPLACEMENTS = [
    # ------------------------------------------------------------ surfaces
    # Every background in KaTrain goes through this mixin, so depth is added
    # here once: `elevation` casts a shadow, `gloss` lights the surface from
    # above, and `sunken` turns it into a well.
    ('''<BackgroundMixin>:
    canvas.before:
        Color:
            rgba: root.background_color
        RoundedRectangle:
            size: self.size
            pos: self.pos
            radius: [root.background_radius, ]
''', '''<BackgroundMixin>:
    elevation: 0
    gloss: 0
    sunken: 0
    # Layers that are switched off are given no area, so they cost nothing to draw.
    canvas.before:
        Color:
            rgba: (0, 0, 0, 0.42 * min(1, root.elevation) * root.background_color[3])
        BorderImage:
            texture: kx.shadow()
            border: [kx.SHADOW_BORDER] * 4
            display_border: [max(1, dp(11) * root.elevation)] * 4
            pos: self.x - dp(11) * root.elevation, self.y - dp(14) * root.elevation
            size: (self.width + dp(22) * root.elevation, self.height + dp(22) * root.elevation) if root.elevation else (0, 0)
        Color:
            rgba: root.background_color
        RoundedRectangle:
            size: self.size if root.background_color[3] else (0, 0)
            pos: self.pos
            radius: [root.background_radius, ]
        Color:
            rgba: (1, 1, 1, root.gloss * root.background_color[3])
        RoundedRectangle:
            size: self.size if root.gloss else (0, 0)
            pos: self.pos
            radius: [root.background_radius, ]
            texture: kx.gloss()
        Color:
            rgba: (1, 1, 1, root.sunken * root.background_color[3])
        RoundedRectangle:
            size: self.size if root.sunken else (0, 0)
            pos: self.pos
            radius: [root.background_radius, ]
            texture: kx.inset()
'''),

    # ------------------------------------------------------------- buttons
    ('''<ToggleButtonMixin>:
    inactive_background_color: Theme.BACKGROUND_COLOR
    active_background_color: Theme.BOX_BACKGROUND_COLOR
''', '''<ToggleButtonMixin>:
    inactive_background_color: (0, 0, 0, 0)
    active_background_color: kx.SURFACE_HIGH
'''),
    ('''<SizedRectangleButton>:
    outline_color: Theme.BUTTON_BORDER_COLOR
    text_color: self.outline_color

<AutoSizedRectangleButton>:
    outline_color: Theme.BUTTON_BORDER_COLOR
    text_color: self.outline_color

<SizedRectangleToggleButton>:
    inactive_outline_color: Theme.BUTTON_INACTIVE_COLOR
    active_outline_color: Theme.BUTTON_BORDER_COLOR
    text_color: self.outline_color

<AutoSizedRectangleToggleButton>:
    inactive_outline_color: Theme.BUTTON_INACTIVE_COLOR
    active_outline_color: Theme.BUTTON_BORDER_COLOR
    text_color: self.outline_color

<SizedRoundedRectangleButton@SizedRectangleButton>:
    background_radius: self.height/3.5

<AutoSizedRoundedRectangleButton@AutoSizedRectangleButton>:
    background_radius: self.height/3.5
''', '''# Keys: raised, lit from above, and they go down when pressed.
<SizedRectangleButton>:
    outline_color: kx.EDGE
    text_color: Theme.BUTTON_BORDER_COLOR
    background_color: kx.BUTTON if self.state == 'normal' else kx.darker(kx.BUTTON, 0.06)
    background_radius: self.height/4
    elevation: 0.9 if self.state == 'normal' else 0.15
    gloss: 1

<AutoSizedRectangleButton>:
    outline_color: kx.EDGE
    text_color: Theme.BUTTON_BORDER_COLOR
    background_color: kx.BUTTON if self.state == 'normal' else kx.darker(kx.BUTTON, 0.06)
    background_radius: self.height/4
    elevation: 0.9 if self.state == 'normal' else 0.15
    gloss: 1
    padding_x: dp(12)

# Tabs: the ones that are on sit raised in their own colour, the rest lie flat.
<SizedRectangleToggleButton>:
    inactive_outline_color: (0, 0, 0, 0)
    active_outline_color: Theme.BUTTON_BORDER_COLOR
    text_color: self.active_outline_color if self.state == 'down' else Theme.BUTTON_INACTIVE_COLOR
    background_radius: self.height/3
    elevation: 0.5 if self.state == 'down' else 0
    gloss: 1 if self.state == 'down' else 0

<AutoSizedRectangleToggleButton>:
    inactive_outline_color: (0, 0, 0, 0)
    active_outline_color: Theme.BUTTON_BORDER_COLOR
    text_color: self.active_outline_color if self.state == 'down' else Theme.BUTTON_INACTIVE_COLOR
    background_radius: self.height/3
    elevation: 0.5 if self.state == 'down' else 0
    gloss: 1 if self.state == 'down' else 0
    padding_x: dp(9)

<SizedRoundedRectangleButton@SizedRectangleButton>:
    background_radius: self.height/3.2

<AutoSizedRoundedRectangleButton@AutoSizedRectangleButton>:
    background_radius: self.height/3.2
'''),

    # --------------------------------------------- bar below the board
    ('''<BadukPanControls>:
    katrain: app.gui
    circles: [black_circle,white_circle]
    mid_circles_container: mid_circles_container
    pass_btn: pass_btn
''', '''<BadukPanControls>:
    katrain: app.gui
    circles: [black_circle,white_circle]
    mid_circles_container: mid_circles_container
    pass_btn: pass_btn
    canvas.before:
        Color:
            rgba: (0, 0, 0, 0.6 * self.opacity)
        BorderImage:
            texture: kx.shadow()
            border: [kx.SHADOW_BORDER] * 4
            display_border: [dp(13)] * 4
            pos: self.x + dp(10) - dp(13), self.y + dp(6) - dp(17)
            size: self.width - dp(20) + dp(26), self.height - dp(10) + dp(26)
        Color:
            rgba: kx.BAR
        RoundedRectangle:
            pos: self.x + dp(10), self.y + dp(6)
            size: self.width - dp(20), self.height - dp(10)
            radius: [(self.height - dp(10)) / 2]
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.x + dp(10), self.y + dp(6)
            size: self.width - dp(20), self.height - dp(10)
            radius: [(self.height - dp(10)) / 2]
            texture: kx.gloss()
        Color:
            rgba: kx.EDGE
        Line:
            rounded_rectangle: (self.x + dp(10), self.y + dp(6), self.width - dp(20), self.height - dp(10), (self.height - dp(10)) / 2)
            width: 1
'''),

    # ------------------------------------------------------- player cards
    ('''    background_color: Theme.BOX_BACKGROUND_COLOR if self.active else Theme.BACKGROUND_COLOR
    outline_color: Theme.BOX_BACKGROUND_COLOR
    outline_width: 2
    padding: [2*CP_PADDING,CP_PADDING,CP_PADDING,CP_PADDING]
''', '''    background_color: kx.SURFACE_HIGH if self.active else kx.SURFACE
    outline_color: kx.ACCENT if self.active else kx.EDGE
    outline_width: 1.5 if self.active else 1
    background_radius: dp(11)
    elevation: 1 if self.active else 0.45
    gloss: 1
    padding: [2*CP_PADDING,CP_PADDING,CP_PADDING,CP_PADDING]
'''),

    # ------------------------------------------------------------- clock
    ('''<Timer>:
    spacing: CP_SPACING
    padding: CP_PADDING * 4, CP_PADDING * 2
''', '''<Timer>:
    spacing: CP_SPACING
    padding: CP_PADDING * 4, CP_PADDING * 2
    background_color: kx.SUNKEN
    background_radius: dp(11)
    sunken: 1
'''),
    ('''            TimerLabel:
                color: Theme.BACKGROUND_COLOR
''', '''            TimerLabel:
                color: kx.lighter(kx.SUNKEN, 0.045)
'''),

    # -------------------------------------------------------- stats, text
    ('''<StatsBox>
    orientation: 'vertical'
    background_color: Theme.BOX_BACKGROUND_COLOR
''', '''<StatsBox>
    orientation: 'vertical'
    background_color: kx.SURFACE
    background_radius: dp(11)
    elevation: 0.45
    gloss: 0.7
    padding: 0, dp(3)
'''),
    ('''<ScrollableLabel>:
    background_color: Theme.BOX_BACKGROUND_COLOR
    do_scroll_x: False
    scroll_type: ['bars']
    bar_width: 5
    bar_color: Theme.SCROLLBAR_COLOR
    label: label
    canvas.before:
        Color:
            rgba: root.outline_color
        Line:
            rectangle:  (*self.pos,*self.size)
            width: 1
''', '''<ScrollableLabel>:
    background_color: kx.SURFACE
    background_radius: dp(9)
    do_scroll_x: False
    scroll_type: ['bars']
    bar_width: dp(5)
    bar_color: Theme.SCROLLBAR_COLOR
    label: label
'''),
    ('''        padding: 5, 5
        font_size: sp(Theme.NOTES_FONT_SIZE)
        line_height: root.line_height
''', '''        padding: dp(10), dp(7)
        font_size: sp(Theme.NOTES_FONT_SIZE)
        line_height: root.line_height
'''),

    # ------------------------------------------------------- right panel
    ('''    padding: CP_PADDING,CP_PADDING,CP_PADDING,0
    spacing: CP_SPACING
    tab_option_height: max(15,root.height / 30)
''', '''    padding: dp(10), dp(4), dp(12), dp(10)
    spacing: dp(8)
    tab_option_height: max(18,root.height / 27)
'''),
    ('''    BoxLayout: # -- Players
        size_hint_y: None
        height: root.player_box_height
''', '''    BoxLayout: # -- Players
        size_hint_y: None
        height: root.player_box_height
        spacing: dp(8)
'''),
    ('''        BGBoxLayout:
            background_color: Theme.BOX_BACKGROUND_COLOR
            orientation: 'vertical'
            ScrollableLabel:
                id: status
                error: False
                size_hint: 1, None
                height: min(self.parent.height*0.66,self.label.texture_size[1])
                outline_color: Theme.ERROR_BORDER_COLOR if self.error else Theme.INFO_TAB_FONT_COLOR
                background_color: Theme.LIGHTER_BACKGROUND_COLOR
''', '''        BGBoxLayout:
            background_color: kx.SURFACE
            background_radius: dp(11)
            elevation: 0.45
            orientation: 'vertical'
            padding: dp(3)
            spacing: dp(3)
            ScrollableLabel:
                id: status
                error: False
                size_hint: 1, None
                height: min(self.parent.height*0.66,self.label.texture_size[1])
                outline_color: Theme.ERROR_BORDER_COLOR if self.error else (0, 0, 0, 0)
                outline_width: 1.3
                background_color: (0.36, 0.14, 0.14, 1) if self.error else kx.SURFACE_HIGH
'''),

    # ------------------------------------------------------------- graph
    ('''        ScoreGraph:
            id: graph
            opacity: 0 if self.hidden else 1
''', '''        ScoreGraph:
            id: graph
            opacity: 0 if self.hidden else 1
            background_color: kx.SUNKEN
            canvas.before:
                Color:
                    rgba: 1, 1, 1, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(4)]
                    texture: kx.inset()
'''),

    # ------------------------------------------------- toolbar toggles
    ('''<AnalysisToggle>:
    spacing: CP_SPACING
    size_hint: None, 0.7
    width: self.minimum_width
    pos_hint: {'center_y':0.5}
    checkbox: checkbox
    label: label
''', '''<AnalysisToggle>:
    spacing: CP_SPACING
    size_hint: None, 0.74
    width: self.minimum_width
    padding: dp(12), 0, dp(7), 0
    pos_hint: {'center_y':0.5}
    checkbox: checkbox
    label: label
    is_on: checkbox.active and not root.disabled
    canvas.before:
        Color:
            rgba: (0, 0, 0, 0.34 if root.is_on else 0)
        BorderImage:
            texture: kx.shadow()
            border: [kx.SHADOW_BORDER] * 4
            display_border: [dp(8)] * 4
            pos: self.x - dp(8), self.y - dp(10)
            size: (self.width + dp(16), self.height + dp(16)) if root.is_on else (0, 0)
        Color:
            rgba: kx.SURFACE_HIGH if root.is_on else kx.SUNKEN
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height / 2.6]
        Color:
            rgba: (1, 1, 1, 1 if root.is_on else 0)
        RoundedRectangle:
            pos: self.pos
            size: self.size if root.is_on else (0, 0)
            radius: [self.height / 2.6]
            texture: kx.gloss()
        Color:
            rgba: kx.ACCENT if root.is_on else kx.EDGE
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, self.height / 2.6)
            width: 1.2 if root.is_on else 1
'''),
    ('''                text: i18n._('analysis:territory')
                padding: 0,0,show_children.width/8,0 # space button a bit more
''', '''                text: i18n._('analysis:territory')
'''),
    ('''            spacing: root.height/4
            AnalysisToggle:
                id: show_children
''', '''            spacing: root.height/6
            AnalysisToggle:
                id: show_children
'''),
    ('''                AutoSizedRectangleButton:
                    background_color: Theme.BOX_BACKGROUND_COLOR
                    size_hint_y: 0.55
''', '''                AutoSizedRectangleButton:
                    size_hint_y: 0.62
'''),

    # ------------------------------------------------ play / analyse switch
    ('''<PlayAnalyzeButton@SizedToggleButton>:
    inactive_background_color: Theme.BOX_BACKGROUND_COLOR
    active_background_color: Theme.PLAY_ANALYZE_TAB_COLOR
    ripple_color: Theme.BACKGROUND_COLOR
    text_color: self.inactive_background_color if self.state=='down' else self.active_background_color
''', '''<PlayAnalyzeButton@SizedToggleButton>:
    inactive_background_color: (0, 0, 0, 0)
    active_background_color: kx.ACCENT
    ripple_color: Theme.BACKGROUND_COLOR
    text_color: (0.13, 0.10, 0.04, 1) if self.state=='down' else kx.TEXT_DIM
    background_radius: self.height / 2.8
    elevation: 0.8 if self.state=='down' else 0
    gloss: 1 if self.state=='down' else 0
'''),
    ('''    OutlineBox:
        size_hint: 0.7,0.7
        pos_hint: {'center_x':0.5,'center_y':0.45}
''', '''    OutlineBox:
        size_hint: 0.88,0.74
        pos_hint: {'center_x':0.5,'center_y':0.5}
        background_color: kx.SUNKEN
        background_radius: self.height / 2.4
        sunken: 1
        padding: dp(4)
        spacing: dp(4)
'''),

    # --------------------------------------------------------- main window
    ('''                BGBoxLayout:
                    background_color: Theme.BACKGROUND_COLOR
                    BoxLayout:
                        orientation: 'vertical'
                        AnalysisControls:
                            id: analysis_controls
''', '''                BGBoxLayout:
                    background_color: (0, 0, 0, 0)
                    canvas.before:
                        Color:
                            rgba: 1, 1, 1, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                            texture: kx.table()
                    BoxLayout:
                        orientation: 'vertical'
                        AnalysisControls:
                            id: analysis_controls
                            padding: dp(6), 0
'''),
    ('''                        ControlsPanel:
                            id: controls
        NavigationDrawer:
''', '''                        KaTrainExplainerPanel:
                            id: explainer_panel
                            katrain: root
                            size_hint_y: None
                            height: max(dp(78), 0.088 * root.height)
                        ControlsPanel:
                            id: controls
        NavigationDrawer:
'''),
]


def apply(source):
    """Return the redesigned kv source for the original KaTrain v1.20.0 ``gui.kv`` text."""
    newline = '\r\n' if '\r\n' in source else '\n'
    text = source.replace('\r\n', '\n')
    for old, new in REPLACEMENTS:
        if text.count(old) != 1:
            raise ValueError('界面文件与预期不符，未修改。 / gui.kv does not match the expected layout near: '
                             + old.strip().splitlines()[0])
        text = text.replace(old, new)
    first_line, rest = text.split('\n', 1)
    text = first_line + '\n' + MARKER + '\n' + IMPORTS + rest
    return text.replace('\n', newline)
