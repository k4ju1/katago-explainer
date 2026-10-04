"""Chinese-first glossary; definitions describe concepts, not verified move effects.

Definitions are original summaries checked against the association references
below. Callers choose term IDs from their evidence; this module classifies no
board shapes and makes no automatic life/death or positional judgments.
"""


GLOSSARY_SOURCES = (
    {'title': '日本棋院：基本囲碁用語 / Nihon Ki-in: Basic Go Terms',
     'url': 'https://www.nihonkiin.or.jp/teach/lesson/school/yogo.html'},
    {'title': '日本棋院：角部第一手 / Nihon Ki-in: Opening Corner Points',
     'url': 'https://www.nihonkiin.or.jp/teach/lesson/school/joban01.html'},
    {'title': '日本棋院：打吃与提子 / Nihon Ki-in: Atari and Capture',
     'url': 'https://www.nihonkiin.or.jp/teach/lesson/school/atari.html'},
    {'title': '日本棋院：劫 / Nihon Ki-in: Ko',
     'url': 'https://www.nihonkiin.or.jp/teach/lesson/school/ko.html'},
    {'title': '英国围棋协会：术语表 / British Go Association: Glossary',
     'url': 'https://www.britgo.org/bgj/glossary.html'},
    {'title': '英国围棋协会：术语释义 / British Go Association: Term Definitions',
     'url': 'https://www.britgo.org/general/definitions.html'},
)


# Values are immutable: Chinese name, English name, Chinese/English definition.
_TERMS = {
    'joseki': ('定式', 'Joseki',
        '通常在角部、基于特定前提双方各有所得的常见应对序列；是否合局仍需看全盘。',
        'A studied local sequence, usually in a corner, considered reasonable for both sides under its starting conditions; full-board context still matters.'),
    'star_point': ('星位', 'Corner star point (4-4)',
        '角部定式语境中的四四点：距相邻两边各为第四线。',
        'In corner joseki discussions, the 4-4 point lies on the fourth line from each adjacent edge.'),
    'komoku': ('小目', 'Komoku (3-4 point)',
        '角部三四或四三点：距一边为第三线，距另一边为第四线。',
        'A corner 3-4 or 4-3 point: third line from one edge and fourth line from the other.'),
    'approach': ('挂角', 'Approach',
        '向对方已有角部棋子接近的一着，开启角部交涉。',
        'A move approaching an opposing corner stone to begin a local interaction.'),
    'pincer': ('夹击', 'Pincer',
        '从另一侧逼近挂角子，与原有角部棋子形成夹击关系；攻守效果需具体计算。',
        'A play on the other side of an approaching stone, forming a pincer with the corner stone; its effect requires reading.'),
    'invasion_33': ('点三三', '3-3 invasion',
        '进入对方角部三三点的侵入手段；做活与外围取舍取决于后续应对。',
        'An invasion at the 3-3 point in an opposing corner; survival and outside tradeoffs depend on the continuation.'),
    'attach': ('靠', 'Attachment',
        '落在与对方棋子上下左右紧邻的空点；效果取决于气数与应手。',
        'A move immediately beside an opposing stone, sharing an edge; its effect depends on liberties and replies.'),
    'hane': ('扳', 'Hane',
        '围着对方棋子向侧面弯出，通常与己子成斜角关系；须留意断点。',
        'A move bending around an opposing stone, usually diagonal to a friendly stone; cutting points need attention.'),
    'extend': ('长', 'Extend (nobi)',
        '沿直线方向紧邻己子、向外延伸的一着。',
        'A move directly adjoining a friendly stone that extends the stones outward along a line.'),
    'connect': ('粘', 'Solid connection',
        '在连接点补子，把原本分开的己方棋子直接连成一块。',
        'A move filling a connection point to join separate friendly chains directly.'),
    'diagonal': ('尖', 'Diagonal move (kosumi)',
        '与己子斜对角紧邻落子形成的尖形；斜接不等于规则上的直接连接。',
        'A move one step diagonally from a friendly stone; diagonal adjacency does not directly connect chains.'),
    'keima': ('小飞', 'Small knight move (keima)',
        '两落点横纵距离为一格与两格的小飞形；挂角时参照对方角子，展开时通常参照己子。是否可断需看具体配置。',
        'A knight-move offset of one and two grid steps; an approach refers to the opposing corner stone, while development usually refers to a friendly stone. Cutting possibilities depend on the position.'),
    'block': ('挡', 'Block',
        '在对方延伸的方向落子，阻挡其继续展开；能否有效阻挡须看后续应对。',
        'A play in the direction of an opposing extension to block further development; its effectiveness depends on the continuation.'),
    'counter_hane': ('反扳', 'Counter-hane',
        '对方扳后，己方也用扳形应对；应留意双方断点与气数。',
        'A hane played in response to the opponent\'s hane; check cutting points and liberties on both sides.'),
    'kick': ('尖顶', 'Kick',
        '以相对己方角子成尖形的一着顶住对方挂角子；对手如何长出仍需计算。',
        'A diagonal move from a friendly corner stone that contacts the approaching stone; the opponent\'s extension still requires reading.'),
    'jump': ('一间跳', 'One-space jump',
        '沿同一直线与己子隔一个空点的跳；中间空点并未因此直接连通。',
        'A jump along a line with one empty intersection between friendly stones; the empty point does not directly connect the chains.'),
    'three_space_extension': ('拆三', 'Three-space extension',
        '沿边与己方已有棋子隔三个空点展开，常见于两子展开；能否形成根据地需看应手。',
        'A side extension leaving three empty intersections from existing friendly stones, often from a two-stone formation; a viable base still depends on replies.'),
    'extension': ('拆边', 'Side extension',
        '沿边与己方已有棋子保持间隔展开的一着；能否形成根据地需看应对。',
        'A spaced move developing along a side from friendly stones; whether it makes a viable base depends on replies.'),
    'atari': ('打吃', 'Atari',
        '棋块只剩一口气的状态；造成这一状态称打吃，并不等于已经提子。',
        'A chain has only one remaining liberty; putting it in this state is atari, not an already completed capture.'),
    'liberties': ('气', 'Liberties',
        '与棋块上下左右相邻的空点；同一棋块共享这些气。',
        'Empty intersections directly beside a chain along grid lines; all stones in the chain share these liberties.'),
    'ko': ('劫', 'Ko',
        '涉及循环回提的局面；简单劫禁止立即回提，重复局面的限制按所用规则处理。',
        'A position involving repeated recapture; simple ko forbids immediate recapture, while repetition restrictions depend on the rules.'),
    'capture': ('提子', 'Capture',
        '对方棋块最后一口气被占后，按规则将该块棋子从棋盘移除。',
        'When an opposing chain loses its last liberty, its stones are removed under the rules.'),
    'sente': ('先手', 'Sente (initiative)',
        '使对手有必要应对、从而争取主动权的着法或局面；须核对脱先的实际后果。',
        'A move or situation retaining initiative by requiring a reply; verify the consequences if the opponent plays elsewhere.'),
    'thickness': ('厚势', 'Thickness',
        '较稳健、向外发挥作用的棋形；能否形成厚势须结合弱点、后续变化与全局判断。',
        'A strong formation exerting outward influence; judging thickness requires checking weaknesses, continuations, and the full board.'),
}


def get_terms(ids):
    """Return bilingual rows in requested order, without duplicates.

    `ids` may be an iterable of IDs, one string, or None. Unknown and non-string
    IDs are ignored. Fresh nested dictionaries prevent callers from changing
    later results. Inclusion explains a term; it does not certify a move's effect.
    """
    if ids is None:
        return []
    if isinstance(ids, str):
        ids = [ids]
    result, seen = [], set()
    for term_id in ids:
        if not isinstance(term_id, str) or term_id in seen or term_id not in _TERMS:
            continue
        seen.add(term_id)
        zh, en, definition_zh, definition_en = _TERMS[term_id]
        result.append({'id': term_id, 'term': {'zh': zh, 'en': en},
                       'definition': {'zh': definition_zh, 'en': definition_en}})
    return result
