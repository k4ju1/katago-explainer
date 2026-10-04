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
    'shusaku_kosumi': ('秀策尖', 'Shusaku kosumi',
        '小目受小飞挂角后朝外侧的经典尖应法；这是局部命名应手，不代表完整秀策流布局或当前最佳选择。',
        'A named diagonal response to a low approach to a 3-4 point; it identifies a local response, not a complete Shusaku opening or the best move in this game.'),
    'attach_retreat': ('托退定式', 'Attachment-and-retreat joseki',
        '小目一间高挂后的托、扳、退变化；实粘、虎接、拆边等还有不同分支，是否合局要看全盘。',
        'An attachment-hane-retreat sequence after a high approach to a 3-4 point; connection and extension branches vary with whole-board context.'),
    'mi_flying_dagger': ('芈氏飞刀', "Mi's Flying Dagger",
        '星位点三三中含尖入、外扳等分支的复杂接触战变化；本目录只核对外扳入口，不推断征子有利或必胜。',
        'A complex 3-3 contact-fighting family with diagonal-entry and outward-hane branches; this catalog checks one outward-hane entry without asserting favorable ladders or forced victory.'),
    'high_approach': ('一间高挂', 'One-space high approach',
        '在第四线、与小目角子沿边隔一个空点的高挂；可选择托退等不同应法。',
        'A fourth-line high approach leaving one empty intersection along the side from the 3-4 corner stone; attachment-and-retreat is one possible response family.'),
    'attach_under': ('托', 'Attachment underneath',
        '从靠近边角的一侧接触对方棋子；二路托指落在第二线的这类接触手段，效果需看应手。',
        'An attachment from the edge or corner side of an opposing stone; a second-line attachment is one example, with its effect depending on replies.'),
    'retreat': ('退', 'Retreat',
        '向己方原有配置的方向退回一着，以处理接触或加强联络；是否直接连通须核对棋盘。',
        'A move retreating toward a friendly formation to handle contact or support links; direct connection must be checked on the board.'),
    'cut': ('断', 'Cut',
        '在对方联络处落子，阻碍其连接或分开棋子；能否吃住断下的棋子还需算气与征子。',
        'A play interrupting an opposing connection or separating stones; capturing the separated stones still requires reading liberties and ladders.'),
    'push': ('顶', 'Push',
        '沿接触方向向对方棋子顶出的一着；可能推进棋形，也须注意反扳、断点及气数。',
        'A move pushing into an opposing stone along a contact direction; check counter-hanes, cuts, and liberties.'),
    'ladder': ('征子', 'Ladder',
        '连续打吃迫使棋块沿阶梯路径逃跑的追击；全盘路径上的配合子或引征子可能改变结果。',
        'A chasing sequence of repeated atari along a stair-like path; stones and ladder breakers along the whole-board path can change its outcome.'),
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
    'tenuki': ('脱先', 'Tenuki (playing elsewhere)',
        '不在刚才的局部继续应对，转到棋盘别处落子；是否成立取决于局部留下的后续手段有多大。',
        'Leaving the current local exchange to play elsewhere on the board; whether that works depends on how large the local follow-up is.'),
    'gote': ('后手', 'Gote',
        '下完之后对手不必在局部应对、可以转向别处的着法或局面；与先手相对，须核对脱先的实际后果。',
        'A move or situation after which the opponent need not answer locally and may play elsewhere; the opposite of sente, to be verified against the consequences of playing away.'),
    'shoulder_hit': ('肩冲', 'Shoulder hit',
        '落在对方棋子斜上方、更靠中腹一路的着法，常用来从上方限制对方的发展；效果要看应手。',
        'A move diagonally above an opposing stone, one line nearer the center, often used to limit its development from above; the effect depends on the replies.'),
    'two_space_jump': ('二间跳', 'Two-space jump',
        '沿同一直线与己子隔两个空点的跳；步子比一间跳大，联络也更薄。',
        'A jump along a line leaving two empty intersections between friendly stones; faster than a one-space jump but more thinly linked.'),
    'large_knight': ('大飞', 'Large knight move (ogeima)',
        '两落点横纵距离为一格与三格的大飞形；比小飞展开得更远，被分断的余地也更大。',
        'A knight-like offset of one and three grid steps; it reaches farther than a small knight move and leaves more room to be separated.'),
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
