/* Original cutaway gags for the replay.

   A step.cutaway cue picks one gag from a small pool. The pick is a hash of
   the game number, the cue, and how many times that cue has already fired,
   so the same game always shows the same scene. The player interrupts the
   tally, draws the scene, then comes back.

   Jokes and drawings here are original. No borrowed characters or catchphrases.
*/
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.YahtzeeCutaways = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function hash(text) {
    var h = 2166136261;
    var value = String(text);
    for (var i = 0; i < value.length; i++) {
      h ^= value.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function where(ctx, prep) {
    return ctx.venue ? " " + prep + " " + ctx.venue : "";
  }

  var GAGS = {
    yahtzee: [
      {
        id: "lamppost",
        ms: 2800,
        scene: "lamp",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " tried to high-five a lamppost, and the lamppost won.";
        },
      },
      {
        id: "pigeon",
        ms: 3200,
        scene: "pigeon",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " called a parade" + where(ctx, "outside") + ", and the only marcher was a pigeon in a paper hat.";
        },
      },
      {
        id: "fruit-bowl",
        ms: 2600,
        scene: "fruit",
        line: function (ctx) {
          var spot = ctx.venue ? " at " + ctx.venue : " on the table";
          return "This is like the time the fruit bowl" + spot + " stood up and took a bow.";
        },
      },
      {
        id: "cape-sock",
        ms: 3000,
        scene: "sock",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " found a sock so proud it asked for a tiny cape.";
        },
      },
    ],
    bonus: [
      {
        id: "balloons",
        ms: 2600,
        scene: "balloons",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " hit the bonus and a bunch of balloons showed up uninvited.";
        },
      },
      {
        id: "tiny-bell",
        ms: 2400,
        scene: "bell",
        line: function (ctx) {
          return "This is like the time a tiny bell rang and " + ctx.who + " bowed to it by mistake.";
        },
      },
      {
        id: "applause-stairs",
        ms: 3000,
        scene: "stairs",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " climbed a staircase" + where(ctx, "at") + " that was mostly applause.";
        },
      },
      {
        id: "big-star",
        ms: 2800,
        scene: "star",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " got a gold star so big it needed its own chair.";
        },
      },
    ],
    scratch: [
      {
        id: "sorry-bus",
        ms: 3200,
        scene: "bus",
        line: function (ctx) {
          var spot = ctx.venue ? " outside " + ctx.venue : "";
          return "This is like the time " + ctx.who + " left the " + ctx.label.toLowerCase() + " on a bus" + spot + ", and the bus looked sorry.";
        },
      },
      {
        id: "polite-moth",
        ms: 2800,
        scene: "moth",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " opened the box and a very polite moth flew out.";
        },
      },
      {
        id: "cushion",
        ms: 2600,
        scene: "cushion",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " aimed for the " + ctx.label.toLowerCase() + " and sat on a cushion instead.";
        },
      },
      {
        id: "not-today",
        ms: 3000,
        scene: "map",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " followed a map that just said not today.";
        },
      },
    ],
    comeback: [
      {
        id: "jetpack-tortoise",
        ms: 3200,
        scene: "tortoise",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " came back on a tortoise wearing a very small jetpack.";
        },
      },
      {
        id: "umbrella",
        ms: 2800,
        scene: "umbrella",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " turned it around" + where(ctx, "outside") + " with a well-timed umbrella.";
        },
      },
      {
        id: "hero-sandwich",
        ms: 2600,
        scene: "sandwich",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " was behind, then a heroic sandwich changed everything.";
        },
      },
      {
        id: "painted-door",
        ms: 3000,
        scene: "door",
        line: function (ctx) {
          return "This is like the time " + ctx.who + " came back through a door nobody remembered painting.";
        },
      },
    ],
  };

  function titleFor(cue, who) {
    if (cue === "yahtzee") return who + "! Yahtzee!";
    if (cue === "bonus") return who + "! Bonus!";
    if (cue === "scratch") return who + " missed it!";
    return who + " is back!";
  }

  function decorate(cutaway, ctx) {
    var pool = GAGS[cutaway.cue];
    if (!pool || !pool.length) return cutaway;
    var gag = pool[hash(ctx.gameSeq + "|" + cutaway.cue + "|" + ctx.index) % pool.length];
    var view = {
      who: ctx.who,
      other: ctx.other,
      venue: ctx.venue || "",
      label: ctx.label || "box",
    };
    cutaway.gag = gag.id;
    cutaway.scene = gag.scene;
    cutaway.ms = gag.ms;
    cutaway.who = view.who;
    cutaway.other = view.other;
    cutaway.title = titleFor(cutaway.cue, view.who);
    cutaway.line = gag.line(view);
    return cutaway;
  }

  function listGags() {
    var rows = [];
    Object.keys(GAGS).forEach(function (cue) {
      GAGS[cue].forEach(function (gag) {
        var base = { who: "Erin", other: "Jordan", venue: "", label: "Large straight" };
        var placed = { who: "Erin", other: "Jordan", venue: "Anchor Bar", label: "Large straight" };
        rows.push({
          cue: cue,
          id: gag.id,
          ms: gag.ms,
          scene: gag.scene,
          title: titleFor(cue, "Erin"),
          line: gag.line(base),
          lineAtVenue: gag.line(placed),
        });
      });
    });
    return rows;
  }

  var NS = "http://www.w3.org/2000/svg";

  function svgNode(name, attrs) {
    var el = document.createElementNS(NS, name);
    Object.keys(attrs).forEach(function (key) { el.setAttribute(key, attrs[key]); });
    return el;
  }

  function person(x, color) {
    var g = svgNode("g", {});
    g.appendChild(svgNode("circle", { cx: x, cy: 46, r: 11, fill: color }));
    g.appendChild(svgNode("rect", { x: x - 9, y: 59, width: 18, height: 26, rx: 6, fill: color }));
    g.appendChild(svgNode("line", { x1: x - 16, y1: 68, x2: x + 16, y2: 64, stroke: color, "stroke-width": 4, "stroke-linecap": "round" }));
    g.appendChild(svgNode("line", { x1: x - 5, y1: 85, x2: x - 9, y2: 108, stroke: color, "stroke-width": 4, "stroke-linecap": "round" }));
    g.appendChild(svgNode("line", { x1: x + 5, y1: 85, x2: x + 10, y2: 108, stroke: color, "stroke-width": 4, "stroke-linecap": "round" }));
    return g;
  }

  function colorOf(name) {
    return name === "Jordan" ? "#2D9CFF" : "#FF2D92";
  }

  function cast(who) {
    if (who === "Erin and Jordan") return [["Erin", 70], ["Jordan", 112]];
    if (who === "Jordan") return [["Jordan", 78]];
    return [["Erin", 78]];
  }

  function addCast(root, who) {
    cast(who).forEach(function (pair) {
      root.appendChild(person(pair[1], colorOf(pair[0])));
    });
  }

  var SCENES = {
    lamp: function (root) {
      root.appendChild(svgNode("rect", { x: 150, y: 28, width: 8, height: 90, rx: 3, fill: "#F3F6FA" }));
      root.appendChild(svgNode("circle", { cx: 154, cy: 24, r: 16, fill: "#FFE56A" }));
      root.appendChild(svgNode("path", { d: "M146 24 h16", stroke: "#12171F", "stroke-width": 2 }));
    },
    pigeon: function (root) {
      root.appendChild(svgNode("ellipse", { cx: 168, cy: 70, rx: 28, ry: 16, fill: "#C5D0E0" }));
      root.appendChild(svgNode("circle", { cx: 190, cy: 62, r: 10, fill: "#C5D0E0" }));
      root.appendChild(svgNode("polygon", { points: "168,42 184,58 152,58", fill: "#F3F6FA" }));
      root.appendChild(svgNode("polygon", { points: "198,62 214,66 198,70", fill: "#FFB020" }));
    },
    fruit: function (root) {
      root.appendChild(svgNode("path", { d: "M140 88 Q168 110 196 88", fill: "none", stroke: "#F3F6FA", "stroke-width": 8, "stroke-linecap": "round" }));
      root.appendChild(svgNode("circle", { cx: 156, cy: 74, r: 10, fill: "#FF5A5A" }));
      root.appendChild(svgNode("circle", { cx: 176, cy: 70, r: 11, fill: "#7DDE6A" }));
      root.appendChild(svgNode("circle", { cx: 192, cy: 78, r: 9, fill: "#FFE56A" }));
    },
    sock: function (root) {
      root.appendChild(svgNode("path", { d: "M150 40 h22 v36 h16 v16 h-38 z", fill: "#F3F6FA" }));
      root.appendChild(svgNode("polygon", { points: "150,40 188,28 168,62", fill: "#FF2D92" }));
    },
    balloons: function (root) {
      root.appendChild(svgNode("circle", { cx: 160, cy: 42, r: 14, fill: "#FF2D92" }));
      root.appendChild(svgNode("circle", { cx: 182, cy: 36, r: 14, fill: "#2D9CFF" }));
      root.appendChild(svgNode("circle", { cx: 172, cy: 58, r: 12, fill: "#FFE56A" }));
      root.appendChild(svgNode("path", { d: "M160 56 C164 80 170 80 172 96 M182 50 C176 78 174 80 172 96", fill: "none", stroke: "#F3F6FA", "stroke-width": 1.5 }));
    },
    bell: function (root) {
      root.appendChild(svgNode("path", { d: "M150 70 Q168 28 186 70 Z", fill: "#FFE56A" }));
      root.appendChild(svgNode("rect", { x: 146, y: 70, width: 44, height: 8, rx: 2, fill: "#F3F6FA" }));
      root.appendChild(svgNode("circle", { cx: 168, cy: 84, r: 5, fill: "#F3F6FA" }));
    },
    stairs: function (root) {
      root.appendChild(svgNode("rect", { x: 140, y: 96, width: 70, height: 12, fill: "#F3F6FA" }));
      root.appendChild(svgNode("rect", { x: 154, y: 80, width: 56, height: 12, fill: "#C5D0E0" }));
      root.appendChild(svgNode("rect", { x: 168, y: 64, width: 42, height: 12, fill: "#8B95A8" }));
    },
    star: function (root) {
      root.appendChild(svgNode("polygon", { points: "176,18 184,42 210,42 190,58 198,84 176,68 154,84 162,58 142,42 168,42", fill: "#FFE56A" }));
      root.appendChild(svgNode("rect", { x: 160, y: 96, width: 32, height: 8, rx: 2, fill: "#C5D0E0" }));
      root.appendChild(svgNode("rect", { x: 172, y: 88, width: 8, height: 10, fill: "#C5D0E0" }));
    },
    bus: function (root) {
      root.appendChild(svgNode("rect", { x: 136, y: 58, width: 84, height: 36, rx: 6, fill: "#FFE56A" }));
      root.appendChild(svgNode("rect", { x: 146, y: 66, width: 16, height: 12, fill: "#12171F" }));
      root.appendChild(svgNode("rect", { x: 168, y: 66, width: 16, height: 12, fill: "#12171F" }));
      root.appendChild(svgNode("circle", { cx: 154, cy: 98, r: 6, fill: "#12171F" }));
      root.appendChild(svgNode("circle", { cx: 196, cy: 98, r: 6, fill: "#12171F" }));
    },
    moth: function (root) {
      root.appendChild(svgNode("ellipse", { cx: 156, cy: 62, rx: 16, ry: 22, fill: "#C5D0E0" }));
      root.appendChild(svgNode("ellipse", { cx: 188, cy: 62, rx: 16, ry: 22, fill: "#C5D0E0" }));
      root.appendChild(svgNode("ellipse", { cx: 172, cy: 64, rx: 5, ry: 16, fill: "#F3F6FA" }));
    },
    cushion: function (root) {
      root.appendChild(svgNode("rect", { x: 140, y: 86, width: 72, height: 22, rx: 10, fill: "#7DDE6A" }));
    },
    map: function (root) {
      root.appendChild(svgNode("rect", { x: 142, y: 36, width: 70, height: 54, rx: 4, fill: "#F3F6FA" }));
      root.appendChild(svgNode("path", { d: "M154 70 C166 50 178 78 196 52", fill: "none", stroke: "#FF2D92", "stroke-width": 3 }));
    },
    tortoise: function (root) {
      root.appendChild(svgNode("ellipse", { cx: 176, cy: 78, rx: 26, ry: 16, fill: "#7DDE6A" }));
      root.appendChild(svgNode("circle", { cx: 198, cy: 70, r: 8, fill: "#C5D0E0" }));
      root.appendChild(svgNode("rect", { x: 168, y: 52, width: 10, height: 16, rx: 2, fill: "#8B95A8" }));
      root.appendChild(svgNode("rect", { x: 160, y: 58, width: 8, height: 6, fill: "#FFB020" }));
    },
    umbrella: function (root) {
      root.appendChild(svgNode("path", { d: "M150 58 Q172 28 194 58 Z", fill: "#2D9CFF" }));
      root.appendChild(svgNode("line", { x1: 172, y1: 58, x2: 172, y2: 96, stroke: "#F3F6FA", "stroke-width": 3 }));
    },
    sandwich: function (root) {
      root.appendChild(svgNode("rect", { x: 146, y: 58, width: 52, height: 10, rx: 3, fill: "#E7C48A" }));
      root.appendChild(svgNode("rect", { x: 150, y: 68, width: 44, height: 8, fill: "#7DDE6A" }));
      root.appendChild(svgNode("rect", { x: 146, y: 76, width: 52, height: 10, rx: 3, fill: "#E7C48A" }));
      root.appendChild(svgNode("polygon", { points: "198,58 214,48 206,78", fill: "#FF2D92" }));
    },
    door: function (root) {
      root.appendChild(svgNode("rect", { x: 148, y: 36, width: 48, height: 78, rx: 3, fill: "#C5D0E0" }));
      root.appendChild(svgNode("circle", { cx: 184, cy: 78, r: 4, fill: "#FFE56A" }));
    },
  };

  function render(cutaway) {
    if (!cutaway || typeof document === "undefined") return null;
    var draw = SCENES[cutaway.scene];
    if (!draw) return null;
    var root = svgNode("svg", { viewBox: "0 0 240 130", class: "cutaway-art", "aria-hidden": "true" });
    draw(root);
    addCast(root, cutaway.who);
    return root;
  }

  return {
    GAGS: GAGS,
    hash: hash,
    decorate: decorate,
    titleFor: titleFor,
    listGags: listGags,
    render: render,
  };
});
