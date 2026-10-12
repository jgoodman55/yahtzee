/* Box-by-box replay.

   buildTimeline() is the whole model: a list of timed steps, then a finale.
   mount() only draws that list. A later pass can add dice, sound, or a
   different drawing style onto a step without changing the page or the
   story picker.

   Each box step:
     kind, t, box, label, points, running, margin, focus, caption, holdMs, cutaway
   t is milliseconds from the start. margin is Jordan minus Erin.
   focus is true when the game story names that box.

   cutaway is null, or { cue } where cue is "yahtzee", "bonus", "scratch",
   or "comeback". That is the hook for a later cutaway scene. This player
   does not draw one. A later pass can pick an original gag from the cue.
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
  var NORMAL_MS = 700;
  var FOCUS_MS = 1400;
  var COMEBACK_DEFICIT = 25;
  var FULL = {
    yahtzee: 50,
    large_straight: 40,
    small_straight: 30,
    full_house: 25,
    upper_bonus: 35,
  };

  function cutawayFor(box, erinPoints, jordanPoints, previousMargin, margin) {
    if (box === "yahtzee" && (erinPoints === 50 || jordanPoints === 50)) {
      return { cue: "yahtzee" };
    }
    if (box === "upper_bonus" && (erinPoints === 35 || jordanPoints === 35)) {
      return { cue: "bonus" };
    }
    var full = FULL[box];
    if (full && ((erinPoints === 0 && jordanPoints === full) || (jordanPoints === 0 && erinPoints === full))) {
      return { cue: "scratch" };
    }
    var comeback = (previousMargin <= -COMEBACK_DEFICIT && margin > 0) ||
      (previousMargin >= COMEBACK_DEFICIT && margin < 0);
    if (comeback) return { cue: "comeback" };
    return null;
  }

  function pointsOf(scores, key) {
    if (!scores) return 0;
    var value = scores[key];
    return value == null ? 0 : Number(value) || 0;
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
        cutaway: cutawayFor(key, erinPoints, jordanPoints, previousMargin, margin),
      };
      previousMargin = margin;
      t += holdMs;
      return step;
    });
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
      cutaways: steps.filter(function (step) { return step.cutaway; }).map(function (step) {
        return { t: step.t, box: step.box, cue: step.cutaway.cue };
      }),
    };
  }

  function prefersReducedMotion() {
    return !!(
      root.matchMedia &&
      root.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function mount(container, timeline, options) {
    options = options || {};
    var reduced = options.reduced != null ? options.reduced : prefersReducedMotion();
    var timer = null;
    var playing = false;

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

    function stop() {
      if (timer) clearTimeout(timer);
      timer = null;
      playing = false;
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
      // step.cutaway is the later scene hook. Nothing is drawn for it here.
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
      if (reduced) {
        finish();
        return;
      }
      playing = true;
      button.disabled = true;
      button.textContent = "Playing";
      var index = 0;
      showStep(0, true);
      function next() {
        index += 1;
        if (index >= timeline.steps.length) {
          finish();
          return;
        }
        showStep(index, true);
        timer = setTimeout(next, timeline.steps[index].holdMs);
      }
      timer = setTimeout(next, timeline.steps[0].holdMs);
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
    buildTimeline: buildTimeline,
    mount: mount,
    leadLine: leadLine,
    scoreLine: scoreLine,
  };
});
