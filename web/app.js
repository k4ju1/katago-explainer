(() => {
  "use strict";
  const $ = (id) => document.getElementById(id),
    esc = (s) =>
      String(s ?? "").replace(
        /[&<>"']/g,
        (c) =>
          ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
          })[c],
      );
  const labels = {
    zh: {
      brandSubtitle: "着法 · 棋理 · 后续变化",
      heroTitle: "这一步，为什么这样下？",
      heroText: "看棋理，走变化，对照胜率。",
      connecting: "正在连接本地 KataGo",
      loadingGame: "正在读取示例棋局…",
      demo: "开局示例",
      upload: "打开 SGF",
      positionHeading: "棋盘与变化",
      beforeMove: "第",
      moveUnit: "手前",
      lastMove: "上一手",
      targetMove: "讲解着法",
      numberedPV: "数字为后续变化手顺",
      boardHint: "点击空点可比较自己的候选。",
      actualChoice: "实战着法",
      aiChoice: "AI 一选",
      analyze: "解释这一步 →",
      variations: "后续怎样演变",
      variationHint: "切换变化，对照同一个局面的不同选择。",
      play: "播放",
      pause: "暂停",
      pvCaveat: "这是引擎当前搜索到的参考变化，实战对手可能采用其他应对。",
      winrateHeading: "沿变化的胜率",
      chartCaveat: "每个局面独立搜索；变化包含搜索波动，不代表单手的精确贡献。",
      whyHeading: "为什么这样下",
      whySubtitle: "结论、依据与后续变化，一起看。",
      emptyTitle: "从一手棋开始",
      emptyText:
        "选择实战着法或 AI 一选，再点击“解释这一步”。每条棋理都能回到具体局面与搜索依据。",
      flow1: "棋盘事实",
      flow2: "后续变化",
      flow3: "胜率对照",
      scopeNote: "讲解来自规则核验和 KataGo 搜索；推测会单独标注。",
      evidenceHeading: "棋理与证据",
      candidateHeading: "同局面的候选比较",
      rawDetails: "查看分析详情",
      footer: "KataGo 评估与变化 · 可核验的棋理解释",
      localFooter: "本地运行 · 棋谱留在本机",
      uploadTitle: "打开你的棋谱",
      uploadText: "选择 SGF 文件，或粘贴 SGF 内容。当前读取棋谱主线。",
      loadGame: "读取棋谱",
      ready: "KataGo 就绪",
      unavailable: "本地服务未连接",
      black: "黑棋",
      white: "白棋",
      toPlay: "行棋",
      actual: "实战",
      custom: "候选",
      noActual: "当前局面没有实战着法，可讲解 AI 一选",
      loading: "正在读取棋谱…",
      analyzing: "KataGo 正在搜索…",
      done: "分析完成",
      failed: "分析未完成",
      selected: "所选着法",
      ai: "AI 一选",
      winrate: "胜率",
      score: "目差",
      points: "目",
      visits: "搜索次数",
      comparison: "相对替代着法",
      fixed: "视角固定为",
      step: "变化",
      initial: "起始局面",
      move: "着法",
      limitations: "解释的边界",
      verified: "棋盘事实",
      search: "搜索支持",
      uncertain: "证据不足",
      evidence: "证据",
      emptySGF: "请先选择 SGF 文件或粘贴棋谱。",
      uploadFail: "棋谱读取失败",
      noResult: "服务没有返回完整分析结果。",
      thinking: "正在准备搜索…",
      variationDisplay: "正在查看变化",
      helpError: "请保留错误提示，并检查启动窗口中 KataGo 是否正常运行。",
      candidateTip: "此处比较同一局面的不同首着；不能与沿变化的波动混为一谈。",
      loaded: "已读取棋谱",
      classicPattern: "经典棋形",
      patternBasic: "点三三",
      patternKick: "尖顶",
      patternMi: "芈氏飞刀",
      patternAttachRetreat: "托退",
      patternShusaku: "秀策尖",
      heroEyebrow: "一步棋，一条有据可查的解释",
      whyEyebrow: "棋理有依据",
      examples: "示例棋谱",
      captureDemo: "提子示例",
      loadPattern: "打开所选定式",
      overviewTab: "结论",
      evidenceTab: "依据",
      josekiTab: "定式·术语",
      limitsTab: "边界",
      metricCaption: "胜率与目差固定为被讲解方视角，差值来自同局面的候选补搜。",
      evidenceHint: "带着法链接的依据，可直接跳到棋盘验证。",
      noJoseki: "这手未匹配当前定式目录，可查看下方术语与“依据”。",
      evalDetails: "逐手评估数值",
      moveValue: "这一手的价值",
      moveFollowup: "对方脱先之后",
      prevPosition: "上一局面",
      nextPosition: "下一局面",
      movePosition: "棋谱位置",
      moveNumber: "手数",
      choiceGroup: "选择讲解着法",
      inspectorSections: "讲解内容",
      pvStart: "变化起点",
      pvPrev: "上一手变化",
      pvNext: "下一手变化",
      pvEnd: "变化终点",
      close: "关闭",
      sgfFile: "SGF 文件",
      sgfContent: "SGF 内容",
    },
    en: {
      brandSubtitle: "Moves · Reasons · Continuations",
      heroTitle: "Why play this move?",
      heroText: "Read the reason. Replay the line. Compare the outcome.",
      connecting: "Connecting to local KataGo",
      loadingGame: "Loading the example game…",
      demo: "Opening sample",
      upload: "Open SGF",
      positionHeading: "Board & variations",
      beforeMove: "Before",
      moveUnit: "",
      lastMove: "Last move",
      targetMove: "Move to explain",
      numberedPV: "Numbers show the continuation",
      boardHint: "Click an empty point to compare your own candidate.",
      actualChoice: "Played move",
      aiChoice: "AI first choice",
      analyze: "Explain this move →",
      variations: "What happens next",
      variationHint: "Switch lines to compare choices from the same position.",
      play: "Play",
      pause: "Pause",
      pvCaveat:
        "This is a reference line from the current search. Your opponent may choose other replies.",
      winrateHeading: "Winrate along the line",
      chartCaveat:
        "Each position is searched independently. Changes include search noise, not an exact contribution per move.",
      whyHeading: "Why this move",
      whySubtitle: "The verdict, the evidence, and what happens next.",
      emptyTitle: "Start with one move",
      emptyText:
        "Choose the played move or AI first choice, then explain it. Trace each reason to a board position and search evidence.",
      flow1: "Board facts",
      flow2: "Continuation",
      flow3: "Winrate comparison",
      scopeNote:
        "Explanations use board checks and KataGo search. Interpretations are labeled separately.",
      evidenceHeading: "Reasons and evidence",
      candidateHeading: "Candidates from the same position",
      rawDetails: "View analysis details",
      footer: "KataGo search · Replayable evidence",
      localFooter: "Runs locally · Your SGF stays here",
      uploadTitle: "Open your game",
      uploadText:
        "Select an SGF file or paste its contents. The main game line is read.",
      loadGame: "Load game",
      ready: "KataGo ready",
      unavailable: "Local service unavailable",
      black: "Black",
      white: "White",
      toPlay: "to play",
      actual: "Played",
      custom: "Candidate",
      noActual: "No played move here. You can explain the AI first choice.",
      loading: "Reading game…",
      analyzing: "KataGo is searching…",
      done: "Analysis complete",
      failed: "Analysis incomplete",
      selected: "Chosen move",
      ai: "AI first choice",
      winrate: "Winrate",
      score: "Score lead",
      points: "points",
      visits: "Visits",
      comparison: "Compared with alternative",
      fixed: "Fixed perspective:",
      step: "Step",
      initial: "Starting position",
      move: "Move",
      limitations: "Limits of this explanation",
      verified: "Board fact",
      search: "Search-supported",
      uncertain: "Insufficient evidence",
      evidence: "Evidence",
      emptySGF: "Select an SGF file or paste a game first.",
      uploadFail: "Could not read the game",
      noResult: "The service did not return a complete result.",
      thinking: "Preparing the search…",
      variationDisplay: "Showing continuation",
      helpError:
        "Keep this error message and check whether KataGo is running in the launcher window.",
      candidateTip:
        "These are different first moves from the same position. They are separate from changes along a continuation.",
      loaded: "Game loaded",
      classicPattern: "Classic pattern",
      patternBasic: "3-3 invasion",
      patternKick: "Kick",
      patternMi: "Mi's Flying Dagger",
      patternAttachRetreat: "Attach and retreat",
      patternShusaku: "Shusaku diagonal",
      heroEyebrow: "ONE MOVE. A REASON YOU CAN TRACE.",
      whyEyebrow: "REASON & EVIDENCE",
      examples: "Sample games",
      captureDemo: "Capture sample",
      loadPattern: "Open selected pattern",
      overviewTab: "Overview",
      evidenceTab: "Evidence",
      josekiTab: "Joseki & terms",
      limitsTab: "Limits",
      metricCaption:
        "Values keep the explained player’s perspective. Differences compare candidate searches from the same position.",
      evidenceHint: "Move links take you to the corresponding board position.",
      noJoseki:
        "No match in the current joseki catalog. Explore the terminology and Evidence tab.",
      evalDetails: "Per-move evaluations",
      moveValue: "Value of this move",
      moveFollowup: "If the opponent plays away",
      prevPosition: "Previous position",
      nextPosition: "Next position",
      movePosition: "Move position",
      moveNumber: "Move number",
      choiceGroup: "Move to explain",
      inspectorSections: "Explanation sections",
      pvStart: "Start of variation",
      pvPrev: "Previous variation move",
      pvNext: "Next variation move",
      pvEnd: "End of variation",
      close: "Close",
      sgfFile: "SGF file",
      sgfContent: "SGF content",
    },
  };
  const state = {
    lang: localStorage.getItem("katago-language") === "en" ? "en" : "zh",
    game: null,
    index: 0,
    choice: "actual",
    custom: null,
    result: null,
    branch: 0,
    step: 0,
    job: null,
    busy: false,
    playTimer: null,
    positionKey: null,
    inspector: "overview",
  };
  function tr(key) {
    return labels[state.lang][key] ?? key;
  }
  function text(value) {
    if (value == null) return "";
    if (typeof value === "string" || typeof value === "number")
      return String(value);
    return value[state.lang] ?? value.en ?? value.zh ?? "";
  }
  function number(n, d = 1) {
    return n != null && Number.isFinite(Number(n)) ? Number(n).toFixed(d) : "—";
  }
  function rate(n) {
    return n == null ? "—" : number(n, 1) + "%";
  }
  function moveText(move) {
    return typeof move === "string"
      ? move
      : Array.isArray(move)
        ? move[1]
        : (move?.move ?? "pass");
  }
  function movePlayer(m) {
    return Array.isArray(m) ? m[0] : m?.player;
  }
  function playerText(p) {
    return String(p || "B")
      .toUpperCase()
      .startsWith("W")
      ? tr("white")
      : tr("black");
  }
  function gameMoves() {
    return state.game?.moves || [];
  }
  function gameId() {
    return state.game?.id;
  }
  function size() {
    return Number(state.game?.board_size ?? 19);
  }
  function gamePosition(index) {
    return (
      state.game?.positions?.[index] ?? {
        stones: [],
        toPlay: movePlayer(gameMoves()[index]) ?? "B",
      }
    );
  }
  function actor() {
    const pos = gamePosition(state.index);
    return (
      state.result?.player ??
      pos.toPlay ??
      movePlayer(gameMoves()[state.index]) ??
      (state.index % 2 ? "W" : "B")
    );
  }
  function key() {
    return (
      gameId() + ":" + state.index + ":" + state.choice + ":" + state.custom
    );
  }
  function branches() {
    return state.result?.branches ?? [];
  }
  function branch() {
    return branches()[state.branch] || null;
  }
  function branchMoves(b) {
    return b?.steps?.filter((s) => s.ply > 0) ?? [];
  }
  function branchPosition(b, step) {
    return (
      b?.steps?.find((s) => s.ply === step)?.board ?? state.result?.base_board
    );
  }
  function branchLabel(b, i) {
    return (
      text(b.label) || (i === 0 ? tr("selected") : tr("custom") + " " + (i + 1))
    );
  }
  function stopPlay() {
    clearInterval(state.playTimer);
    state.playTimer = null;
    $("pvPlay").textContent = tr("play");
  }
  function applyLanguage() {
    document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
    document
      .querySelectorAll("[data-i18n]")
      .forEach((el) => (el.textContent = tr(el.dataset.i18n)));
    document
      .querySelectorAll("[data-i18n-aria]")
      .forEach((el) => el.setAttribute("aria-label", tr(el.dataset.i18nAria)));
    $("language").textContent =
      state.lang === "zh" ? "中文 · EN" : "中 · English";
    renderGame();
    if (state.result) renderResult();
    renderBoard();
    if (state.busy) renderProgress();
    if (state.playTimer) $("pvPlay").textContent = tr("pause");
  }
  async function api(path, body) {
    const response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("HTTP " + response.status);
    }
    if (!response.ok)
      throw new Error(
        text(data.error ?? data.message) || "HTTP " + response.status,
      );
    return data;
  }
  function setStatus(message, error = false, progress = null) {
    $("statusArea").classList.remove("hidden");
    $("statusArea").classList.toggle("error", error);
    $("statusText").textContent = message;
    $("progressTrack").classList.toggle("hidden", progress == null);
    if (progress != null)
      $("progressBar").style.width = Math.max(0, Math.min(100, progress)) + "%";
  }
  function busy(value, status = value ? "analyzing" : "ready") {
    state.busy = value;
    if (value) state.progress = null;
    $("workspace").classList.toggle("busy", value);
    document
      .querySelectorAll(
        ".choice, #moveSlider, #moveNumber, #prevMove, #nextMove, #demoButton, #captureButton, #josekiExample, #josekiButton, #uploadButton",
      )
      .forEach((el) => (el.disabled = value));
    $("engineDot").classList.toggle("busy", value);
    $("engineStatus").dataset.i18n = status;
    $("engineStatus").textContent = tr(status);
    $("analyzeButton").disabled = value || !state.game;
    if (state.game) renderGame();
  }
  function resetResult() {
    stopPlay();
    state.result = null;
    state.positionKey = null;
    state.step = 0;
    setInspector("overview");
    $("explanationContent").classList.add("hidden");
    $("emptyExplanation").classList.remove("hidden");
    $("variationPanel").classList.add("hidden");
    $("chartPanel").classList.add("hidden");
    $("statusArea").classList.add("hidden");
  }
  function setGame(game, defaults = {}) {
    state.game = game;
    state.index = Math.min(
      gameMoves().length,
      Math.max(0, Number(defaults.move_index ?? gameMoves().length)),
    );
    state.choice =
      defaults.choice ?? (gameMoves()[state.index] ? "actual" : "ai");
    if (state.choice === "actual" && !gameMoves()[state.index])
      state.choice = "ai";
    state.custom = null;
    resetResult();
    document.querySelector(".sample-menu").open = false;
    renderGame();
    renderBoard();
  }
  function renderGame() {
    if (!state.game) return;
    const g = state.game;
    const moves = gameMoves();
    $("gameName").textContent = text(g.name) || "SGF";
    $("gameMeta").textContent = [
      size() + " × " + size(),
      text(g.rules),
      g.komi != null ? "Komi " + g.komi : null,
      moves.length + " " + (state.lang === "zh" ? "手" : "moves"),
    ]
      .filter(Boolean)
      .join(" · ");
    $("gameWarnings").textContent = (g.warnings ?? []).map(text).join(" ");
    $("gameWarnings").classList.toggle("hidden", !g.warnings?.length);
    $("boardSize").textContent = size() + " × " + size();
    $("moveSlider").max = moves.length;
    $("moveSlider").value = state.index;
    $("moveNumber").max = moves.length + 1;
    $("moveNumber").value = state.index + 1;
    $("prevMove").disabled = state.busy || state.index === 0;
    $("nextMove").disabled = state.busy || state.index >= moves.length;
    const pos = gamePosition(state.index),
      p =
        pos.toPlay ??
        movePlayer(moves[state.index]) ??
        (state.index % 2 ? "W" : "B");
    $("toPlay").classList.toggle(
      "white",
      String(p).toUpperCase().startsWith("W"),
    );
    $("toPlay").querySelector("span").textContent =
      playerText(p) + " " + tr("toPlay");
    const actual = moves[state.index];
    $("selectedMoveLabel").textContent = actual
      ? tr("actual") + " " + moveText(actual)
      : tr("noActual");
    document.querySelectorAll("[data-choice]").forEach((el) => {
      el.classList.toggle("active", el.dataset.choice === state.choice);
      el.setAttribute(
        "aria-pressed",
        String(el.dataset.choice === state.choice),
      );
    });
    document.querySelector('[data-choice="actual"]').disabled =
      state.busy || !actual;
    $("customChoice").classList.toggle("hidden", !state.custom);
    $("customChoice").textContent = tr("custom") + " " + state.custom;
    $("analyzeButton").disabled = state.busy;
  }
  function changeIndex(value) {
    if (state.busy) return;
    state.index = Math.max(0, Math.min(gameMoves().length, Number(value) || 0));
    state.custom = null;
    if (!gameMoves()[state.index] && state.choice === "actual")
      state.choice = "ai";
    if (state.choice === "custom")
      state.choice = gameMoves()[state.index] ? "actual" : "ai";
    resetResult();
    renderGame();
    renderBoard();
  }
  function gtpToXY(move) {
    const m = String(move || "").toUpperCase();
    if (m === "PASS" || m === "RESIGN") return null;
    const col = "ABCDEFGHJKLMNOPQRSTUVWXYZ".indexOf(m[0]),
      row = Number(m.slice(1));
    return col >= 0 && row >= 1 && row <= size() && col < size()
      ? { x: col, y: size() - row }
      : null;
  }
  function xyToGTP(x, y) {
    return "ABCDEFGHJKLMNOPQRSTUVWXYZ"[x] + (size() - y);
  }
  function boardStones(position) {
    return position?.stones ?? [];
  }
  function renderBoard() {
    const n = size(),
      pad = 39,
      unit = 562 / (n - 1);
    const point = (x, y) => ({ x: pad + x * unit, y: pad + y * unit });
    const line = state.result && state.positionKey === key() ? branch() : null;
    const position = line
      ? branchPosition(line, state.step)
      : gamePosition(state.index);
    const stones = boardStones(position);
    const svg = [
      `<defs>
      <radialGradient id="bStone" cx="34%" cy="28%" r="72%"><stop offset="0" stop-color="#4b514c"/><stop offset=".55" stop-color="#202721"/><stop offset="1" stop-color="#111611"/></radialGradient>
      <radialGradient id="wStone" cx="33%" cy="24%" r="72%"><stop offset="0" stop-color="#ffffff"/><stop offset=".73" stop-color="#f4f1e9"/><stop offset="1" stop-color="#d0cbbf"/></radialGradient>
      <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="1" dy="2" stdDeviation="1.2" flood-opacity=".3"/></filter>
    </defs><rect width="640" height="640" fill="#dfbd7f"/>`,
    ];
    for (let i = 0; i < n; i++) {
      const k = pad + i * unit,
        letter = "ABCDEFGHJKLMNOPQRSTUVWXYZ"[i];
      svg.push(`<path d="M ${pad} ${k} H ${640 - pad} M ${k} ${pad} V ${640 - pad}" stroke="#68542f" stroke-width="1" opacity=".72"/>
        <text x="${k}" y="20" text-anchor="middle" font-size="11" fill="#6d5936">${letter}</text>
        <text x="${k}" y="627" text-anchor="middle" font-size="11" fill="#6d5936">${letter}</text>
        <text x="17" y="${k + 4}" text-anchor="middle" font-size="11" fill="#6d5936">${n - i}</text>
        <text x="623" y="${k + 4}" text-anchor="middle" font-size="11" fill="#6d5936">${n - i}</text>`);
    }
    const starLines = n === 19 ? [3, 9, 15] : n === 13 ? [3, 6, 9] : [2, 4, 6];
    for (const x of starLines)
      for (const y of starLines) {
        if (n !== 19 && (x === starLines[1]) !== (y === starLines[1])) continue;
        const p = point(x, y);
        svg.push(`<circle cx="${p.x}" cy="${p.y}" r="3" fill="#6a552f"/>`);
      }
    for (const stone of stones) {
      const p = point(stone.x, stone.y),
        white = stone.player === "W";
      svg.push(
        `<circle cx="${p.x}" cy="${p.y}" r="${unit * 0.46}" fill="url(#${white ? "w" : "b"}Stone)" stroke="${white ? "#bdb7a6" : "#131a14"}" stroke-width=".7" filter="url(#shadow)"/>`,
      );
    }
    const last =
      position?.lastMove ??
      (!line && state.index ? moveText(gameMoves()[state.index - 1]) : null);
    const lastPoint = gtpToXY(last);
    if (lastPoint) {
      const p = point(lastPoint.x, lastPoint.y);
      svg.push(
        `<circle cx="${p.x}" cy="${p.y}" r="${unit * 0.17}" fill="none" stroke="#5fab82" stroke-width="2.5"/>`,
      );
    }
    if (line && state.step > 0) {
      const labels = new Map();
      branchMoves(line)
        .slice(0, state.step)
        .forEach((move, index) => {
          const xy = gtpToXY(move.move);
          if (xy) labels.set(`${xy.x},${xy.y}`, { xy, number: index + 1 });
        });
      for (const { xy, number } of labels.values()) {
        const stone = stones.find(
          (stone) => stone.x === xy.x && stone.y === xy.y,
        );
        if (!stone) continue;
        const p = point(xy.x, xy.y);
        svg.push(
          `<text x="${p.x}" y="${p.y + unit * 0.16}" text-anchor="middle" font-size="${unit * 0.44}" font-weight="700" fill="${stone.player === "W" ? "#243b2c" : "#fffdf0"}">${number}</text>`,
        );
      }
    } else {
      const target = gtpToXY(
        line
          ? line.move
          : state.choice === "custom"
            ? state.custom
            : state.choice === "actual"
              ? moveText(gameMoves()[state.index])
              : null,
      );
      if (target) {
        const p = point(target.x, target.y),
          r = unit * 0.24;
        svg.push(
          `<path d="M ${p.x} ${p.y - r} L ${p.x + r} ${p.y + r * 0.8} L ${p.x - r} ${p.y + r * 0.8} Z" fill="#984d36" stroke="#f9efda" stroke-width="1.2"/>`,
        );
      }
    }
    $("board").innerHTML = svg.join("");
    const toPlay = position?.toPlay ?? actor();
    $("toPlay").classList.toggle("white", toPlay === "W");
    $("toPlay").querySelector("span").textContent =
      playerText(toPlay) + " " + tr("toPlay");
    $("board").setAttribute(
      "aria-label",
      `${state.lang === "zh" ? "围棋棋盘" : "Go board"}, ${n} × ${n}`,
    );
    $("boardNote").textContent =
      line && state.step > 0
        ? `${tr("variationDisplay")} · ${branchLabel(line, state.branch)} · ${state.step} / ${branchMoves(line).length}`
        : tr("boardHint");
  }
  function renderJoseki(explanation) {
    const matches = explanation.joseki,
      terms = explanation.terms;
    const local = (zh, en) => (state.lang === "zh" ? zh : en);
    $("josekiArea").classList.toggle("hidden", !matches.length);
    $("noJoseki").classList.toggle("hidden", !!matches.length);
    const sourceLink = (source) => {
      const title = text(source.title),
        url = source.url;
      let safe = false;
      try {
        safe = ["http:", "https:"].includes(new URL(url).protocol);
      } catch {}
      return `<div class="joseki-source">${esc(local("出处：", "Source: "))}${
        safe
          ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(title || url)}</a>`
          : esc(title)
      }</div>`;
    };
    $("josekiArea").innerHTML = matches.length
      ? `<h3 class="section-label">${esc(local("定式关联", "Joseki reference"))}</h3>
      <p class="reference-caveat">${esc(local("以下是定式参照手顺，独立于 KataGo 搜索变化。定式名称不等于本局最佳选择。★ 标出讲解的一手。", "Reference sequences are separate from KataGo search lines. A recognized joseki does not establish the best move here. ★ marks the explained move."))}</p>
      ${matches
        .map(
          (match) => `<article class="joseki-reference">
        <h3>${esc(text(match.name))}</h3><p class="joseki-meta">${esc(
          ["corner", "stage", "relation"]
            .map((key) => text(match[key]))
            .filter(Boolean)
            .join(" · "),
        )}</p>
        <p class="joseki-role"><strong>${esc(local("本手作用：", "This move’s role: "))}</strong>${esc(text(match.move_role))}</p>
        <p class="joseki-role">${esc(text(match.move_explanation))}</p>
        <div class="small">${esc(local("定式参考手顺", "Joseki reference sequence"))}</div>
        <ol class="joseki-line">${match.reference_line.map((step) => `<li class="${step.selected ? "selected" : ""}">${step.selected ? "★ " : ""}${step.ply}. ${esc(playerText(step.player))} ${esc(step.move)} — ${esc(text(step.role))}</li>`).join("")}</ol>
        ${match.sources.map(sourceLink).join("")}
        <ul class="joseki-notes">${match.notes.map((note) => `<li>${esc(text(note))}</li>`).join("")}</ul>
      </article>`,
        )
        .join("")}`
      : "";
    $("termsArea").classList.toggle("hidden", !terms.length);
    $("termsArea").innerHTML = terms.length
      ? `<h3 class="section-label">${esc(local("围棋术语", "Go terminology"))}</h3>
      <dl class="glossary">${terms.map((term) => `<div><dt>${esc(text(term.term))}</dt><dd>${esc(text(term.definition))}</dd></div>`).join("")}</dl>`
      : "";
  }
  function setInspector(name, focus = false) {
    state.inspector = name;
    document.querySelectorAll("[data-inspector-tab]").forEach((tab) => {
      const selected = tab.dataset.inspectorTab === name;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      $(tab.getAttribute("aria-controls")).hidden = !selected;
      if (selected && focus) tab.focus();
    });
  }
  function renderClaims(target, reasons, compact = false) {
    $(target).innerHTML = reasons
      .map((reason, index) => {
        const label = compact
          ? tr(reason.id === "move-value" ? "moveValue" : "moveFollowup")
          : reason.level === "reference"
            ? state.lang === "zh"
              ? "定式参考"
              : "Joseki reference"
            : tr(
                reason.level === "board"
                  ? "verified"
                  : reason.level === "tentative"
                    ? "uncertain"
                    : "search",
              );
        return `<article class="claim" data-level="${esc(reason.level)}">
          <div class="claim-title"><span class="claim-index">${index + 1}</span><h3>${esc(label)}</h3></div>
          <p>${esc(text(reason.text))}</p>
          <div class="evidence-links"><span>${esc(tr("evidence"))} ${esc(reason.id)}</span>${reason.ply != null ? `<button data-evidence-ply="${Number(reason.ply)}">${esc(tr("step"))} ${Number(reason.ply)} ↗</button>` : ""}</div>
        </article>`;
      })
      .join("");
    $(target)
      .querySelectorAll("[data-evidence-ply]")
      .forEach(
        (el) =>
          (el.onclick = () => {
            stopPlay();
            state.branch = 0;
            setStep(Number(el.dataset.evidencePly));
            $("boardWrap").scrollIntoView({
              block: "center",
              behavior: "smooth",
            });
          }),
      );
  }
  function renderResult() {
    const result = state.result;
    if (!result || state.positionKey !== key()) return;
    setStatus(`${tr("done")} · ${number(result.elapsed_seconds)} s`);
    const selected = result.selected;
    const chosenMove = result.selected_move;
    const candidates = [selected, result.alternative].filter(Boolean);
    const explanation = result.explanation;
    $("explanationMeta").textContent =
      `${playerText(actor())} · ${tr("selected")} ${chosenMove} · ${number(result.elapsed_seconds)} s`;
    $("answerSummary").textContent = text(explanation.summary);
    const metrics = [
      {
        label: `${chosenMove} · ${tr("winrate")}`,
        value: rate(selected.winrate),
      },
      {
        label: tr("score"),
        value: `${Number(selected.score_lead) > 0 ? "+" : ""}${number(selected.score_lead)} ${tr("points")}`,
      },
    ];
    if (result.comparison) {
      const difference = Number(result.comparison.winrate_pp);
      metrics.push({
        label: `${tr("comparison")} ${result.alternative.move}`,
        value: `${difference > 0 ? "+" : ""}${number(difference)} ${state.lang === "zh" ? "百分点" : "pp"}`,
      });
    }
    $("metrics").innerHTML = metrics
      .map(
        (metric) =>
          `<div class="metric"><div class="label">${esc(metric.label)}</div><div class="value">${esc(metric.value)}</div></div>`,
      )
      .join("");
    renderJoseki(explanation);
    const highlights = explanation.reasons.filter((reason) =>
      ["move-value", "followup-if-ignored"].includes(reason.id),
    );
    renderClaims("overviewReasons", highlights, true);
    renderClaims("claims", explanation.reasons);
    $("candidateArea").classList.toggle("hidden", !candidates.length);
    $("candidateTable").innerHTML =
      `<table class="candidate-table"><thead><tr><th>${esc(tr("move"))}</th><th>${esc(tr("winrate"))}</th><th>${esc(tr("score"))}</th><th>${esc(tr("visits"))}</th></tr></thead><tbody>${candidates.map((candidate) => `<tr class="${candidate.move === chosenMove ? "selected" : ""}"><td><strong>${esc(candidate.move)}</strong>${candidate.move === result.ai_move ? ` · ${esc(tr("ai"))}` : ""}</td><td>${rate(candidate.winrate)}</td><td>${number(candidate.score_lead)}</td><td>${esc(candidate.visits)}</td></tr>`).join("")}</tbody></table>`;
    $("candidateNote").textContent =
      `${tr("candidateTip")} ${tr("fixed")} ${playerText(actor())}`;
    const limitations = [...explanation.limitations, ...result.warnings];
    $("limitations").classList.toggle("hidden", !limitations.length);
    $("limitations").innerHTML =
      `<strong>${esc(tr("limitations"))}</strong><ul>${limitations.map((item) => `<li>${esc(text(item))}</li>`).join("")}</ul>`;
    $("continuationNotes").innerHTML = explanation.continuation
      .map((note) => `<p>${esc(text(note))}</p>`)
      .join("");
    $("rawDetails").textContent = JSON.stringify(result, null, 2);
    $("emptyExplanation").classList.add("hidden");
    $("explanationContent").classList.remove("hidden");
    setInspector(state.inspector);
    renderVariation();
    renderBoard();
  }
  function renderVariation() {
    const line = branch();
    $("variationPanel").classList.toggle("hidden", !line);
    if (!line) {
      $("chartPanel").classList.add("hidden");
      return;
    }
    const moves = branchMoves(line);
    state.step = Math.min(state.step, moves.length);
    $("branchTabs").innerHTML = branches()
      .map(
        (item, index) =>
          `<button data-branch="${index}" class="${state.branch === index ? "active" : ""}" aria-pressed="${state.branch === index}">${esc(branchLabel(item, index))}</button>`,
      )
      .join("");
    $("branchTabs")
      .querySelectorAll("[data-branch]")
      .forEach(
        (button) =>
          (button.onclick = () => {
            stopPlay();
            state.branch = Number(button.dataset.branch);
            state.step = 0;
            renderVariation();
            renderBoard();
          }),
      );
    $("pvStepLabel").textContent = state.step
      ? `${tr("step")} ${state.step} / ${moves.length}`
      : tr("initial");
    $("pvStart").disabled = $("pvPrev").disabled = state.step === 0;
    $("pvNext").disabled = $("pvEnd").disabled = state.step >= moves.length;
    $("pvPlay").disabled = !moves.length;
    $("sequence").innerHTML =
      `<button data-step="0" class="${state.step === 0 ? "active" : ""}">${esc(tr("initial"))}</button>` +
      moves
        .map(
          (move) =>
            `<button data-step="${move.ply}" class="${state.step === move.ply ? "active" : ""}"><span class="stone-dot ${move.player === "W" ? "white" : ""}"></span>${move.ply}. ${esc(move.move)}</button>`,
        )
        .join("");
    $("sequence")
      .querySelectorAll("[data-step]")
      .forEach(
        (button) =>
          (button.onclick = () => {
            stopPlay();
            setStep(Number(button.dataset.step));
          }),
      );
    renderChart();
  }
  function setStep(step) {
    state.step = Math.max(0, Math.min(branchMoves(branch()).length, step));
    renderVariation();
    renderBoard();
    const current = $("sequence").querySelector(".active");
    if (current)
      current.scrollIntoView({
        block: "nearest",
        inline: "nearest",
        behavior: "smooth",
      });
  }
  function renderChart() {
    const evaluations = branch().steps.filter(
      (step) => step.eval?.winrate != null,
    );
    $("chartPanel").classList.toggle("hidden", !evaluations.length);
    if (!evaluations.length) return;
    $("chartPerspective").textContent = `${tr("fixed")} ${playerText(actor())}`;
    const values = evaluations.map((step) => Number(step.eval.winrate));
    const low = Math.max(0, Math.floor((Math.min(...values) - 3) / 5) * 5);
    const high = Math.min(
      100,
      Math.max(low + 10, Math.ceil((Math.max(...values) + 3) / 5) * 5),
    );
    const maxStep = Math.max(1, ...evaluations.map((step) => step.ply));
    const x = (step) => 42 + (step / maxStep) * 543;
    const y = (value) => 12 + ((high - value) / (high - low)) * 133;
    const svg = [
      `<svg viewBox="0 0 600 175" role="group" aria-label="${esc(tr("winrateHeading"))}">`,
    ];
    for (let i = 0; i <= 4; i++) {
      const value = low + ((high - low) * i) / 4;
      svg.push(
        `<path d="M 42 ${y(value)} H 585" stroke="#e5e9df" stroke-dasharray="3 4"/><text x="34" y="${y(value) + 4}" text-anchor="end" fill="#788278" font-size="10">${number(value, 0)}%</text>`,
      );
    }
    svg.push(
      `<polyline points="${evaluations.map((step) => `${x(step.ply)},${y(step.eval.winrate)}`).join(" ")}" fill="none" stroke="#2d7155" stroke-width="2.3" stroke-linejoin="round"/>`,
    );
    for (const step of evaluations) {
      const current = step.ply === state.step;
      const label = `${tr("step")} ${step.ply} · ${rate(step.eval.winrate)}`;
      svg.push(`<circle data-chart-step="${step.ply}" role="button" tabindex="0" aria-label="${esc(label)}" cx="${x(step.ply)}" cy="${y(step.eval.winrate)}" r="${current ? 5 : 3.5}" fill="${current ? "#245c47" : "#fffefa"}" stroke="#2d7155" stroke-width="2"><title>${esc(label)}</title></circle>
        <text x="${x(step.ply)}" y="167" text-anchor="middle" fill="#788278" font-size="10">${step.ply}</text>`);
    }
    svg.push("</svg>");
    $("chart").innerHTML = svg.join("");
    $("chart")
      .querySelectorAll("[data-chart-step]")
      .forEach((dot) => {
        dot.onclick = () => {
          stopPlay();
          setStep(Number(dot.dataset.chartStep));
        };
        dot.onkeydown = (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            dot.onclick();
          }
        };
      });
    $("evalTable").innerHTML =
      `<table class="eval-table"><thead><tr><th>${esc(tr("step"))}</th><th>${esc(tr("move"))}</th><th>${esc(tr("winrate"))}</th><th>${state.lang === "zh" ? "变化（百分点）" : "Change (pp)"}</th><th>${esc(tr("score"))}</th></tr></thead><tbody>${evaluations
        .map((step, index) => {
          const difference = index
            ? Number(step.eval.winrate) -
              Number(evaluations[index - 1].eval.winrate)
            : null;
          return `<tr class="${step.ply === state.step ? "current" : ""}"><td>${step.ply}</td><td>${esc(step.move ?? tr("initial"))}</td><td>${rate(step.eval.winrate)}</td><td>${difference === null ? "—" : `${difference > 0 ? "+" : ""}${number(difference)}`}</td><td>${number(step.eval.score_lead)}</td></tr>`;
        })
        .join("")}</tbody></table>`;
  }
  function renderProgress(progress = state.progress) {
    if (!progress) return;
    state.progress = progress;
    const value = progress.total
      ? (progress.completed / progress.total) * 100
      : null;
    const message = text(progress.message) || tr("analyzing");
    setStatus(
      message +
        (progress.total ? ` · ${progress.completed} / ${progress.total}` : ""),
      false,
      value,
    );
  }
  async function poll() {
    if (!state.job) return;
    try {
      const data = await api("/api/jobs/" + encodeURIComponent(state.job));
      if (data.status === "complete") {
        state.job = null;
        busy(false);
        if (!data.result) throw new Error(tr("noResult"));
        state.result = data.result;
        state.branch = 0;
        state.step = 0;
        renderResult();
        return;
      }
      if (data.status === "error") {
        state.job = null;
        busy(false);
        setStatus(text(data.error) || tr("failed"), true);
        return;
      }
      renderProgress(data.progress);
      setTimeout(poll, 750);
    } catch (error) {
      state.job = null;
      busy(false);
      setStatus(error.message + " " + tr("helpError"), true);
    }
  }
  async function analyze() {
    if (state.busy || !state.game) return;
    resetResult();
    renderBoard();
    state.positionKey = key();
    busy(true);
    setStatus(tr("thinking"), false, 0);
    try {
      const body = {
        game_id: gameId(),
        move_index: state.index,
        choice: state.choice === "custom" ? "ai" : state.choice,
      };
      if (state.choice === "custom") body.move = state.custom;
      const response = await api("/api/analyze", body);
      state.job = response.job_id;
      if (!state.job) throw new Error(tr("noResult"));
      poll();
    } catch (error) {
      busy(false);
      setStatus(error.message, true);
    }
  }
  async function loadState() {
    if (state.busy) return;
    busy(true, "connecting");
    try {
      const data = await api("/api/state");
      setGame(data.game, data.defaults);
      $("engineDot").classList.add("ok");
      busy(false);
    } catch (error) {
      busy(false, "unavailable");
      $("engineDot").classList.remove("ok");
      $("analyzeButton").disabled = true;
      setStatus(error.message + " " + tr("helpError"), true);
    }
  }
  async function loadSample(kind) {
    if (state.busy) return;
    busy(true, "loading");
    try {
      const url =
        kind === "capture"
          ? "/api/examples/capture"
          : "/api/example/joseki/" +
            encodeURIComponent($("josekiExample").value);
      const sample = await api(url);
      const data = await api("/api/game", { sgf: sample.sgf });
      setGame(data.game, {
        ...data.defaults,
        choice: "actual",
        move_index: sample.move_index ?? 0,
      });
      setStatus(tr("loaded"));
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      busy(false);
    }
  }
  function closeUpload() {
    $("uploadModal").classList.add("hidden");
    $("uploadButton").focus();
  }
  $("language").onclick = () => {
    state.lang = state.lang === "zh" ? "en" : "zh";
    localStorage.setItem("katago-language", state.lang);
    applyLanguage();
  };
  $("prevMove").onclick = () => changeIndex(state.index - 1);
  $("nextMove").onclick = () => changeIndex(state.index + 1);
  $("moveSlider").oninput = (event) => changeIndex(event.target.value);
  $("moveNumber").onchange = (event) =>
    changeIndex(Number(event.target.value) - 1);
  document.querySelectorAll("[data-choice]").forEach(
    (button) =>
      (button.onclick = () => {
        if (state.busy) return;
        state.choice = button.dataset.choice;
        resetResult();
        renderGame();
        renderBoard();
      }),
  );
  document.querySelectorAll("[data-inspector-tab]").forEach((tab) => {
    tab.onclick = () => setInspector(tab.dataset.inspectorTab);
    tab.onkeydown = (event) => {
      const tabs = [...document.querySelectorAll("[data-inspector-tab]")];
      const index = tabs.indexOf(tab);
      const next =
        event.key === "ArrowRight"
          ? (index + 1) % tabs.length
          : event.key === "ArrowLeft"
            ? (index + tabs.length - 1) % tabs.length
            : event.key === "Home"
              ? 0
              : event.key === "End"
                ? tabs.length - 1
                : null;
      if (next !== null) {
        event.preventDefault();
        setInspector(tabs[next].dataset.inspectorTab, true);
      }
    };
  });
  $("analyzeButton").onclick = analyze;
  $("board").onclick = (event) => {
    if (state.busy || !state.game) return;
    const rect = $("board").getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 640;
    const y = ((event.clientY - rect.top) / rect.height) * 640;
    const unit = 562 / (size() - 1);
    const col = Math.round((x - 39) / unit);
    const row = Math.round((y - 39) / unit);
    if (
      col < 0 ||
      row < 0 ||
      col >= size() ||
      row >= size() ||
      Math.abs(x - (39 + col * unit)) > unit * 0.5 ||
      Math.abs(y - (39 + row * unit)) > unit * 0.5
    )
      return;
    if (
      boardStones(gamePosition(state.index)).some(
        (stone) => stone.x === col && stone.y === row,
      )
    )
      return;
    state.custom = xyToGTP(col, row);
    state.choice = "custom";
    resetResult();
    renderGame();
    renderBoard();
  };
  $("pvStart").onclick = () => {
    stopPlay();
    setStep(0);
  };
  $("pvPrev").onclick = () => {
    stopPlay();
    setStep(state.step - 1);
  };
  $("pvNext").onclick = () => {
    stopPlay();
    setStep(state.step + 1);
  };
  $("pvEnd").onclick = () => {
    stopPlay();
    setStep(branchMoves(branch()).length);
  };
  $("pvPlay").onclick = () => {
    if (state.playTimer) {
      stopPlay();
      return;
    }
    if (state.step >= branchMoves(branch()).length) setStep(0);
    $("pvPlay").textContent = tr("pause");
    state.playTimer = setInterval(() => {
      setStep(state.step + 1);
      if (state.step >= branchMoves(branch()).length) stopPlay();
    }, 1100);
  };
  $("uploadButton").onclick = () => {
    if (state.busy) return;
    document.querySelector(".sample-menu").open = false;
    $("uploadModal").classList.remove("hidden");
    $("uploadError").textContent = "";
    $("fileInput").focus();
  };
  $("closeUpload").onclick = closeUpload;
  $("uploadModal").onclick = (event) => {
    if (event.target === $("uploadModal")) closeUpload();
  };
  document.addEventListener("keydown", (event) => {
    if ($("uploadModal").classList.contains("hidden")) return;
    if (event.key === "Escape") {
      closeUpload();
      return;
    }
    if (event.key !== "Tab") return;
    const controls = [
      ...$("uploadModal").querySelectorAll("button, input, textarea"),
    ].filter((el) => !el.disabled);
    const first = controls[0],
      last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    }
    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  $("fileInput").onchange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    $("fileName").textContent = file.name;
    try {
      $("sgfText").value = await file.text();
      $("uploadError").textContent = "";
    } catch (error) {
      $("uploadError").textContent = error.message;
    }
  };
  $("submitSGF").onclick = async () => {
    const sgf = $("sgfText").value.trim();
    if (!sgf) {
      $("uploadError").textContent = tr("emptySGF");
      return;
    }
    $("submitSGF").disabled = true;
    $("uploadError").textContent = tr("loading");
    busy(true, "loading");
    try {
      const data = await api("/api/game", { sgf });
      setGame(data.game, data.defaults);
      closeUpload();
      setStatus(tr("loaded"));
    } catch (error) {
      $("uploadError").textContent = tr("uploadFail") + ": " + error.message;
    } finally {
      $("submitSGF").disabled = false;
      busy(false);
    }
  };
  $("demoButton").onclick = loadState;
  $("captureButton").onclick = () => loadSample("capture");
  $("josekiButton").onclick = () => loadSample("joseki");
  applyLanguage();
  loadState();
})();
