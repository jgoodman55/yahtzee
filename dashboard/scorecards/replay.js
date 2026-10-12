/* Box-by-box replay.

   buildTimeline() is the whole model: a list of timed steps, then a finale.
   mount() only draws that list. A later pass can add dice, sound, or a
   different drawing style onto a step without changing the page or the
   story picker.

   Each box step:
     kind, t, box, label, points, running, margin, focus, caption, holdMs, cutaway
   t is milliseconds from the start. margin is Jordan minus Erin.
   focus is true when the game story names that box.

   cutaway is null, or a scene to play after that box: courtroom, documentary,
   regulars, or sports. At most two scenes are kept, the most dramatic ones.
   YahtzeeCutaways draws the scene. Scene time is not part of durationMs.
   Two scenes leave at least two seconds of the scoreboard between them.
   If the replay runs out of boxes first, the second scene plays after it.
*/
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.YahtzeeReplay = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  var ORDER = [
    ["ones", "Aces"],
    ["twos", "Twos"],
    ["threes", "Threes"],
    ["fours", "Fours"],
    ["fives", "Fives"],
    ["sixes", "Sixes"],
    ["upper_bonus", "Upper bonus"],
    ["three_of_a_kind", "Three of a kind"],
    ["four_of_a_kind", "Four of a kind"],
    ["full_house", "Full house"],
    ["small_straight", "Small straight"],
    ["large_straight", "Large straight"],
    ["yahtzee", "Yahtzee"],
    ["chance", "Chance"],
    ["yahtzee_bonus", "Yahtzee bonus"],
  ];
  function slowed(ms) {
    return Math.round(ms * 4 / 3);
  }
  var NORMAL_MS = slowed(700);
  var FOCUS_MS = slowed(1400);
  var SCENE_MS = slowed(3200);
  var BOARD_GAP_MS = slowed(2000);
  var LEAD_MS = slowed(380);
  var BRIDGE_MS = slowed(420);
  var FIXED_POINTS = { full_house: 25, small_straight: 30, large_straight: 40 };
  var RANK = { documentary: 0, regulars: 1, courtroom: 2, sports: 3 };
  var UPPER_KEYS = ["ones", "twos", "threes", "fours", "fives", "sixes"];

  function pointsOf(scores, key) {
    if (!scores) return 0;
    var value = scores[key];
    return value == null ? 0 : Number(value) || 0;
  }

  function upperTotal(scores) {
    return UPPER_KEYS.reduce(function (sum, key) {
      return sum + pointsOf(scores, key);
    }, 0);
  }

  function place(venue) {
    return venue ? " at " + venue : "";
  }

  function chargeName(step) {
    if (step.box === "yahtzee" || step.box === "yahtzee_bonus") return step.label;
    return step.label.charAt(0).toLowerCase() + step.label.slice(1);
  }

  function collectScenes(steps, game) {
    var venue = game.venue || "";
    var seq = game.game_seq || null;
    var last = steps[steps.length - 1];
    var winner = last.running.erin === last.running.jordan
      ? "tie"
      : last.running.erin > last.running.jordan ? "Erin" : "Jordan";
    var scenes = [];
    var erinScores = (game.erin && game.erin.scores) || {};
    var jordanScores = (game.jordan && game.jordan.scores) || {};

    steps.forEach(function (step, index) {
      var erinPoints = step.points.erin;
      var jordanPoints = step.points.jordan;
      if (step.box === "yahtzee" && (erinPoints === 50 || jordanPoints === 50)) {
        var both = erinPoints === 50 && jordanPoints === 50;
        var who = both ? "Erin and Jordan" : erinPoints === 50 ? "Erin" : "Jordan";
        var line = both
          ? "Rarely seen in the wild, Erin and Jordan have rolled a Yahtzee" + place(venue) + "."
          : "Rarely seen in the wild, the " + who + " has rolled a Yahtzee" + place(venue) + ".";
        scenes.push({
          index: index,
          box: step.box,
          cue: "documentary",
          drama: 80,
          who: who,
          line: line,
          gameSeq: seq,
          venue: venue,
          points: 50,
        });
      }
      if (step.box === "upper_bonus" && (erinPoints === 35) !== (jordanPoints === 35)) {
        var erinGot = erinPoints === 35;
        var whoBonus = erinGot ? "Erin" : "Jordan";
        var other = erinGot ? "Jordan" : "Erin";
        var upper = upperTotal(erinGot ? erinScores : jordanScores);
        var otherUpper = upperTotal(erinGot ? jordanScores : erinScores);
        scenes.push({
          index: index,
          box: step.box,
          cue: "sports",
          drama: 36,
          who: whoBonus,
          other: other,
          upper: upper,
          otherUpper: otherUpper,
          erinUpper: upperTotal(erinScores),
          jordanUpper: upperTotal(jordanScores),
          line: "Sources confirm " + whoBonus + " has reached " + upper +
            " in the upper section" + place(venue) + ". " + other + " has not. More at 11.",
          gameSeq: seq,
          venue: venue,
        });
      }
      if (step.box !== "upper_bonus") {
        var charged = "";
        var otherScore = 0;
        if (erinPoints === 0 && jordanPoints > 0) {
          charged = "Erin";
          otherScore = jordanPoints;
        } else if (jordanPoints === 0 && erinPoints > 0) {
          charged = "Jordan";
          otherScore = erinPoints;
        }
        if (charged) {
          var fixed = FIXED_POINTS[step.box];
          var name = chargeName(step);
          var line = fixed
            ? charged + ", you are charged with throwing away " + fixed + " points on " + name + place(venue) + "."
            : charged + ", you are charged with scoring 0 on " + name + place(venue) + ".";
          scenes.push({
            index: index,
            box: step.box,
            cue: "courtroom",
            drama: fixed || otherScore,
            who: charged,
            points: fixed || 0,
            label: step.label,
            erin: erinPoints,
            jordan: jordanPoints,
            line: line,
            docket: step.label + ". Erin " + erinPoints + ". Jordan " + jordanPoints + ".",
            gameSeq: seq,
            venue: venue,
          });
        }
      }
    });

    if (winner === "Erin" || winner === "Jordan") {
      var hole = 0;
      var leadIndex = -1;
      var deepest = 0;
      var firstAhead = -1;
      var previous = 0;
      steps.forEach(function (step, index) {
        var behind = winner === "Jordan" ? Math.max(0, -step.margin) : Math.max(0, step.margin);
        if (behind > deepest) deepest = behind;
        var ahead = winner === "Jordan" ? step.margin > 0 : step.margin < 0;
        if (ahead && firstAhead < 0) firstAhead = index;
        var wasDeep = winner === "Jordan" ? previous <= -30 : previous >= 30;
        if (wasDeep && ahead && Math.abs(previous) > hole) {
          hole = Math.abs(previous);
          leadIndex = index;
        }
        previous = step.margin;
      });
      var deficit = hole >= 30 ? hole : deepest;
      if (deficit >= 30) {
        var at = leadIndex >= 0 ? leadIndex : (firstAhead >= 0 ? firstAhead : steps.length - 1);
        scenes.push({
          index: at,
          box: steps[at].box,
          cue: "regulars",
          drama: deficit,
          who: winner,
          deficit: deficit,
          line: "Back from " + deficit + " down, " + winner + "? I've seen pints with less fizz.",
          gameSeq: seq,
          venue: venue,
        });
      }
    }
    return scenes;
  }

  function scenePayload(scene, step) {
    return {
      cue: scene.cue,
      drama: scene.drama,
      ms: SCENE_MS,
      who: scene.who || "",
      other: scene.other || "",
      line: scene.line,
      docket: scene.docket || "",
      label: scene.label || (step && step.label) || "",
      points: scene.points || 0,
      deficit: scene.deficit || 0,
      upper: scene.upper || 0,
      otherUpper: scene.otherUpper || 0,
      erinUpper: scene.erinUpper || 0,
      jordanUpper: scene.jordanUpper || 0,
      erin: scene.erin != null ? scene.erin : (step ? step.points.erin : 0),
      jordan: scene.jordan != null ? scene.jordan : (step ? step.points.jordan : 0),
      venue: scene.venue || "",
      gameSeq: scene.gameSeq,
      about: scene.box,
    };
  }

  function assignScenes(steps, scenes) {
    var ranked = scenes.slice().sort(function (a, b) {
      if (b.drama !== a.drama) return b.drama - a.drama;
      if (RANK[a.cue] !== RANK[b.cue]) return RANK[a.cue] - RANK[b.cue];
      return a.index - b.index;
    }).slice(0, 2);
    var used = {};
    ranked.sort(function (a, b) { return a.index - b.index; });
    ranked.forEach(function (scene) {
      var index = scene.index;
      while (index < steps.length && used[index]) index += 1;
      if (index >= steps.length) return;
      used[index] = true;
      steps[index].cutaway = scenePayload(scene, steps[index]);
    });
    return ranked;
  }

  function planPlayback(steps) {
    var gap = BOARD_GAP_MS;
    var pending = -1;
    var actions = [];
    steps.forEach(function (step, index) {
      if (step.cutaway && step.cutaway.cue) pending = index;
      if (pending >= 0 && gap >= BOARD_GAP_MS) {
        actions.push({ index: pending, kind: "scene", wait: LEAD_MS });
        pending = -1;
        actions.push({ index: index, kind: "bridge", wait: BRIDGE_MS });
        gap = BRIDGE_MS;
        return;
      }
      var hold = step.holdMs;
      if (pending >= 0 && gap + hold >= BOARD_GAP_MS) {
        var need = BOARD_GAP_MS - gap;
        if (need > 0) actions.push({ index: index, kind: "board", wait: need });
        actions.push({ index: pending, kind: "scene", wait: 0 });
        pending = -1;
        actions.push({ index: index, kind: "bridge", wait: BRIDGE_MS });
        gap = BRIDGE_MS;
        return;
      }
      actions.push({ index: index, kind: "board", wait: hold });
      gap += hold;
    });
    if (pending >= 0) actions.push({ index: pending, kind: "scene-after", wait: 0 });
    return actions;
  }

  function leadLine(margin) {
    if (margin === 0) return "Level.";
    if (margin > 0) return "Jordan ahead by " + margin + ".";
    return "Erin ahead by " + Math.abs(margin) + ".";
  }

  function scoreLine(erin, jordan) {
    if (erin === jordan) return "Level at " + erin + ".";
    if (jordan > erin) return "Jordan " + jordan + ". Erin " + erin + ".";
    return "Erin " + erin + ". Jordan " + jordan + ".";
  }

  function buildTimeline(game) {
    var erinScores = (game.erin && game.erin.scores) || {};
    var jordanScores = (game.jordan && game.jordan.scores) || {};
    var focus = {};
    (game.focus || []).forEach(function (key) { focus[key] = true; });
    var erin = 0;
    var jordan = 0;
    var t = 0;
    var previousMargin = 0;
    var steps = ORDER.map(function (pair) {
      var key = pair[0];
      var label = pair[1];
      var erinPoints = pointsOf(erinScores, key);
      var jordanPoints = pointsOf(jordanScores, key);
      erin += erinPoints;
      jordan += jordanPoints;
      var margin = jordan - erin;
      var isFocus = !!focus[key];
      var holdMs = isFocus ? FOCUS_MS : NORMAL_MS;
      var step = {
        kind: "box",
        t: t,
        box: key,
        label: label,
        points: { erin: erinPoints, jordan: jordanPoints },
        running: { erin: erin, jordan: jordan },
        margin: margin,
        focus: isFocus,
        caption: label + ". Erin " + erinPoints + ". Jordan " + jordanPoints + ".",
        holdMs: holdMs,
        cutaway: null,
      };
      previousMargin = margin;
      t += holdMs;
      return step;
    });
    var scenes = collectScenes(steps, game);
    assignScenes(steps, scenes);
    var finale = {
      kind: "finale",
      t: t,
      running: { erin: erin, jordan: jordan },
      margin: jordan - erin,
      winner: erin === jordan ? "tie" : erin > jordan ? "Erin" : "Jordan",
      scoreLine: scoreLine(erin, jordan),
      caption: game.story || "",
      holdMs: 0,
      cutaway: null,
    };
    return {
      steps: steps,
      finale: finale,
      durationMs: t,
      maxTotal: Math.max(erin, jordan, 1),
      scenes: scenes,
      cutaways: steps.filter(function (step) { return step.cutaway; }).map(function (step) {
        return { t: step.t, box: step.box, cue: step.cutaway.cue, drama: step.cutaway.drama, about: step.cutaway.about };
      }),
    };
  }

  function prefersReducedMotion() {
    return !!(
      globalThis.matchMedia &&
      globalThis.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function mount(container, timeline, options) {
    options = options || {};
    var reduced = options.reduced != null ? options.reduced : prefersReducedMotion();
    var timer = null;
    var playing = false;
    var generation = 0;
    var overlay = null;

    container.classList.add("replay");
    container.innerHTML = "";

    var head = document.createElement("div");
    head.className = "replay-head";
    var title = document.createElement("h2");
    title.textContent = "Replay";
    var button = document.createElement("button");
    button.type = "button";
    button.className = "replay-btn";
    button.textContent = "Play";
    head.appendChild(title);
    head.appendChild(button);

    var lead = document.createElement("p");
    lead.className = "replay-lead";

    var lanes = document.createElement("div");
    lanes.className = "replay-lanes";
    var laneEls = {};
    ["erin", "jordan"].forEach(function (who) {
      var lane = document.createElement("div");
      lane.className = "lane " + who;
      var name = document.createElement("span");
      name.className = "who";
      name.textContent = who === "erin" ? "Erin" : "Jordan";
      var total = document.createElement("span");
      total.className = "total";
      total.textContent = "0";
      var track = document.createElement("div");
      track.className = "track";
      var fill = document.createElement("div");
      fill.className = "fill";
      track.appendChild(fill);
      lane.appendChild(name);
      lane.appendChild(total);
      lane.appendChild(track);
      lanes.appendChild(lane);
      laneEls[who] = { lane: lane, total: total, fill: fill };
    });

    var caption = document.createElement("p");
    caption.className = "replay-caption";
    caption.setAttribute("aria-live", "polite");

    container.appendChild(head);
    container.appendChild(lead);
    container.appendChild(lanes);
    container.appendChild(caption);

    function closeOverlay() {
      if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
      overlay = null;
      if (document.body) document.body.style.overflow = "";
    }

    function stop() {
      generation += 1;
      if (timer) clearTimeout(timer);
      timer = null;
      playing = false;
      closeOverlay();
    }

    function barWidth(value) {
      return Math.max(0, Math.min(100, (value / timeline.maxTotal) * 100));
    }

    function applyRunning(running, animate) {
      ["erin", "jordan"].forEach(function (who) {
        var els = laneEls[who];
        els.total.textContent = String(running[who]);
        els.fill.style.width = barWidth(running[who]) + "%";
        els.lane.classList.toggle("is-pop", !!animate && running[who] > 0);
      });
    }

    function showStart() {
      stop();
      container.classList.remove("is-focus", "is-done");
      applyRunning({ erin: 0, jordan: 0 }, false);
      lead.textContent = "Level.";
      caption.textContent = "Play to watch each box add up.";
      button.textContent = "Play";
      button.disabled = false;
    }

    function showStep(index, animate) {
      var step = timeline.steps[index];
      if (!step) return;
      container.classList.toggle("is-focus", step.focus);
      container.classList.remove("is-done");
      applyRunning(step.running, animate);
      lead.textContent = leadLine(step.margin);
      caption.textContent = step.caption;
    }

    function finish() {
      stop();
      var end = timeline.finale;
      container.classList.remove("is-focus");
      container.classList.add("is-done");
      applyRunning(end.running, false);
      lead.textContent = end.scoreLine;
      caption.textContent = end.caption || end.scoreLine;
      button.textContent = "Replay";
      button.disabled = false;
    }

    function play() {
      stop();
      var token = generation;
      if (reduced) {
        finish();
        return;
      }
      playing = true;
      button.disabled = true;
      button.textContent = "Playing";
      var actions = planPlayback(timeline.steps);
      var cursor = 0;
      function alive() {
        return token === generation;
      }
      function openScene(step, onDone) {
        if (!globalThis.YahtzeeCutaways) {
          onDone();
          return;
        }
        closeOverlay();
        overlay = document.createElement("div");
        document.body.appendChild(overlay);
        document.body.style.overflow = "hidden";
        var settled = false;
        function done() {
          if (settled || !alive()) return;
          settled = true;
          if (timer) clearTimeout(timer);
          timer = null;
          onDone();
        }
        globalThis.YahtzeeCutaways.mount(overlay, step.cutaway, { onSkip: done });
        timer = setTimeout(done, step.cutaway.ms || SCENE_MS);
      }
      function run() {
        if (!alive()) return;
        if (cursor >= actions.length) {
          finish();
          return;
        }
        var action = actions[cursor];
        cursor += 1;
        if (action.kind === "board") showStep(action.index, true);
        if (action.kind === "board" || action.kind === "bridge") {
          timer = setTimeout(run, action.wait);
          return;
        }
        var step = timeline.steps[action.index];
        function next() {
          if (!alive()) return;
          closeOverlay();
          if (action.kind === "scene-after") finish();
          else run();
        }
        if (action.kind === "scene") showStep(action.index, true);
        timer = setTimeout(function () {
          if (!alive()) return;
          openScene(step, next);
        }, action.wait || 0);
      }
      run();
    }

    button.addEventListener("click", function () {
      if (playing) return;
      play();
    });

    if (reduced) finish();
    else showStart();
    if (options.autoplay && !reduced) play();

    return {
      play: play,
      finish: finish,
      show: function (index) {
        stop();
        button.disabled = false;
        button.textContent = "Replay";
        showStep(index, false);
      },
      timeline: timeline,
      reduced: reduced,
    };
  }

  return {
    ORDER: ORDER,
    NORMAL_MS: NORMAL_MS,
    FOCUS_MS: FOCUS_MS,
    SCENE_MS: SCENE_MS,
    BOARD_GAP_MS: BOARD_GAP_MS,
    planPlayback: planPlayback,
    buildTimeline: buildTimeline,
    mount: mount,
    leadLine: leadLine,
    scoreLine: scoreLine,
  };
});
