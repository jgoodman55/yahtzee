/* Draws one replay cutaway into a full-viewport layer.
   The pictures match the approved stills. Motion is short and ends settled.
*/
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.YahtzeeCutaways = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function reducedMotion() {
    return !!(
      globalThis.matchMedia &&
      globalThis.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function sixDie(size, radius, pip) {
    var mid = size / 2;
    var inset = size * 0.26;
    var spots = [
      [inset, inset], [mid, inset], [size - inset, inset],
      [inset, size - inset], [mid, size - inset], [size - inset, size - inset],
    ];
    return (
      '<rect width="' + size + '" height="' + size + '" rx="' + radius + '" fill="#f4f7fb" />' +
      '<g fill="#1a140e">' +
      spots.map(function (spot) {
        return '<circle cx="' + spot[0] + '" cy="' + spot[1] + '" r="' + pip + '" />';
      }).join("") +
      "</g>"
    );
  }

  function courtroom(scene) {
    var seq = scene.gameSeq ? "GAME " + scene.gameSeq : "GAME";
    return (
      '<div class="stage" aria-hidden="true">' +
        '<svg viewBox="0 0 640 480" preserveAspectRatio="xMidYMid meet">' +
          '<rect width="640" height="480" fill="#090b10" />' +
          '<rect x="0" y="0" width="640" height="250" fill="#10141c" />' +
          '<rect x="70" y="36" width="500" height="8" fill="#2a3344" />' +
          '<g>' +
            '<circle cx="250" cy="168" r="46" fill="#f0c9a0" />' +
            '<path d="M206 156c4-48 84-52 92-6 8-28 46-22 40 16-30 8-78 10-104 2z" fill="#f7f7f7" />' +
            '<path d="M214 150c18-6 40-4 52 6" fill="none" stroke="#1a140e" stroke-width="3" stroke-linecap="round" />' +
            '<circle cx="232" cy="172" r="11" fill="none" stroke="#1a140e" stroke-width="3" />' +
            '<circle cx="268" cy="172" r="11" fill="none" stroke="#1a140e" stroke-width="3" />' +
            '<line x1="243" y1="172" x2="257" y2="172" stroke="#1a140e" stroke-width="3" />' +
            '<circle cx="232" cy="174" r="2.5" fill="#1a140e" />' +
            '<circle cx="268" cy="174" r="2.5" fill="#1a140e" />' +
            '<path d="M236 194c8 6 18 6 26 0" fill="none" stroke="#1a140e" stroke-width="3" stroke-linecap="round" />' +
            '<path d="M188 214c18 40 108 42 128 4" fill="#141820" />' +
            '<rect x="168" y="230" width="168" height="120" rx="8" fill="#141820" />' +
            '<rect x="214" y="230" width="76" height="18" fill="#f3f6fa" />' +
            '<path d="M300 250l46 18" stroke="#f0c9a0" stroke-width="14" stroke-linecap="round" />' +
            '<g transform="translate(348 168) rotate(-28)">' +
              '<g class="gavel">' +
                '<rect x="0" y="26" width="10" height="78" rx="4" fill="#e6c48a" />' +
                '<rect x="-22" y="4" width="54" height="28" rx="8" fill="#8d5a2b" />' +
                '<rect x="-22" y="4" width="54" height="8" rx="4" fill="#c48a4a" />' +
              "</g>" +
            "</g>" +
          "</g>" +
          '<path d="M40 318h560v28c0 10-8 16-18 16H58c-10 0-18-6-18-16z" fill="#6e4b2c" />' +
          '<path d="M24 346h592v70H24z" fill="#4a311c" />' +
          '<path d="M24 346h592v10H24z" fill="#8a6240" />' +
          '<rect x="250" y="368" width="140" height="28" rx="4" fill="#2a2118" />' +
          '<text class="plaque" x="320" y="388" text-anchor="middle" fill="#e6c48a" font-family="Georgia, serif" font-size="16" letter-spacing="2">' + esc(seq) + "</text>" +
          '<rect x="78" y="300" width="36" height="22" rx="3" fill="#c4a574" />' +
        "</svg>" +
      "</div>" +
      '<div class="charge">' +
        (scene.venue ? '<p class="where">' + esc(scene.venue) + "</p>" : "") +
        '<h1></h1>' +
        '<p class="docket"></p>' +
      "</div>"
    );
  }

  function documentary(scene) {
    var dies = [
      ["die-1", "translate(210 175) rotate(-8)", 92, 14, 7],
      ["die-2", "translate(330 150) rotate(6)", 100, 16, 8],
      ["die-3", "translate(470 190) rotate(-4)", 88, 14, 7],
      ["die-4", "translate(280 280) rotate(4)", 86, 14, 6.5],
      ["die-5", "translate(400 300) rotate(-10)", 90, 14, 7],
    ];
    var art = dies.map(function (row) {
      return '<g class="die ' + row[0] + '"><g transform="' + row[1] + '">' + sixDie(row[2], row[3], row[4]) + "</g></g>";
    }).join("");
    var sub = scene.venue ? scene.venue + " · 50" : "50";
    return (
      '<div class="stage" aria-hidden="true">' +
        '<svg viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice">' +
          "<defs>" +
            '<radialGradient id="spot" cx="50%" cy="46%" r="48%">' +
              '<stop offset="0%" stop-color="#1d4a32" />' +
              '<stop offset="55%" stop-color="#0c2218" />' +
              '<stop offset="100%" stop-color="#06110c" />' +
            "</radialGradient>" +
          "</defs>" +
          '<rect width="800" height="500" fill="url(#spot)" />' +
          '<g fill="#0e2a1c" opacity="0.9">' +
            '<ellipse cx="120" cy="390" rx="70" ry="18" />' +
            '<ellipse cx="250" cy="410" rx="90" ry="16" />' +
            '<ellipse cx="620" cy="400" rx="110" ry="20" />' +
            '<path d="M80 360c20-70 40-70 48-10" fill="none" stroke="#143824" stroke-width="8" />' +
            '<path d="M700 340c-30-80-10-90 20-20" fill="none" stroke="#143824" stroke-width="8" />' +
          "</g>" +
          art +
        "</svg>" +
      "</div>" +
      '<p class="species">Game ' + esc(scene.gameSeq || "") + "<span>" + esc(sub) + "</span></p>" +
      '<div class="letterbox"><p class="narration">' + esc(scene.line) + "</p></div>"
    );
  }

  function pint(x, extra) {
    return (
      '<g class="' + extra + '">' +
        '<rect x="' + x + '" y="256" width="26" height="56" rx="3" fill="#e7c56a" />' +
        '<rect x="' + (x - 4) + '" y="248" width="34" height="14" rx="5" fill="#f3f6fa" />' +
      "</g>"
    );
  }

  function regulars(scene) {
    var venue = scene.venue || "";
    var size = venue.length > 14 ? 15 : 22;
    var wide = venue.length > 14;
    var plateX = wide ? 48 : 78;
    var plateW = wide ? 220 : 160;
    var sign = venue
      ? (
        "<g class=\"sign\">" +
          '<line x1="150" y1="0" x2="150" y2="78" stroke="#c4a574" stroke-width="4" />' +
          '<rect x="' + plateX + '" y="78" width="' + plateW + '" height="46" rx="4" fill="#1c1814" stroke="#e1b15a" stroke-width="4" />' +
          '<text class="sign-name" x="158" y="108" text-anchor="middle" fill="#e1b15a" font-family="Georgia, serif" font-size="' + size + '" letter-spacing="1">' + esc(venue) + "</text>" +
        "</g>"
      )
      : "";
    return (
      '<div class="stage" aria-hidden="true">' +
        '<svg viewBox="0 0 800 520" preserveAspectRatio="xMidYMid slice">' +
          '<rect width="800" height="520" fill="#100e0c" />' +
          '<rect x="0" y="0" width="800" height="300" fill="#1a1612" />' +
          sign +
          '<g transform="translate(180 150)">' +
            '<circle cx="70" cy="46" r="36" fill="#f0c9a0" />' +
            '<path d="M40 40c8-28 62-28 64 2-20 4-48 6-64 0z" fill="#d7dde6" />' +
            '<path d="M58 58c6 8 22 8 28 0" fill="none" stroke="#1a140e" stroke-width="3" stroke-linecap="round" />' +
            '<circle cx="58" cy="50" r="3" fill="#1a140e" />' +
            '<circle cx="84" cy="50" r="3" fill="#1a140e" />' +
            '<rect x="28" y="86" width="86" height="90" rx="10" fill="#3c4a44" />' +
          "</g>" +
          '<g transform="translate(360 140)">' +
            '<circle cx="78" cy="58" r="38" fill="#e7b892" />' +
            '<path d="M42 48h74v16H42z" fill="#2a3344" />' +
            '<path d="M48 40c10-24 58-22 66 8" fill="#6d5a48" />' +
            '<path d="M58 78h28" stroke="#6d5a48" stroke-width="6" stroke-linecap="round" />' +
            '<circle cx="64" cy="62" r="3" fill="#1a140e" />' +
            '<circle cx="92" cy="62" r="3" fill="#1a140e" />' +
            '<path d="M66 90c8 4 16 4 24 0" fill="none" stroke="#1a140e" stroke-width="3" stroke-linecap="round" />' +
            '<rect x="36" y="100" width="92" height="96" rx="10" fill="#243044" />' +
          "</g>" +
          '<rect x="0" y="300" width="800" height="28" fill="#6e4b2c" />' +
          '<rect x="0" y="328" width="800" height="192" fill="#3d2918" />' +
          '<rect x="0" y="328" width="800" height="14" fill="#8a6240" />' +
          pint(298, "") +
          pint(488, "pint-raise") +
        "</svg>" +
      "</div>" +
      '<p class="bubble">' + esc(scene.line) + "</p>" +
      '<p class="chalk"></p>'
    );
  }

  function sports(scene) {
    return (
      '<div class="stage" aria-hidden="true">' +
        '<svg viewBox="0 0 800 500" preserveAspectRatio="xMidYMid meet">' +
          '<rect width="800" height="500" fill="#070b14" />' +
          '<rect x="40" y="36" width="250" height="150" rx="8" fill="#12171f" stroke="#2a3344" />' +
          '<text x="165" y="78" text-anchor="middle" fill="#a8b3c5" font-family="system-ui, sans-serif" font-size="16" letter-spacing="2">ERIN</text>' +
          '<text class="erin-upper" x="165" y="132" text-anchor="middle" fill="#ff2d92" font-family="system-ui, sans-serif" font-size="64" font-weight="700">' + esc(scene.erinUpper) + "</text>" +
          '<rect x="510" y="36" width="250" height="150" rx="8" fill="#12171f" stroke="#2a3344" />' +
          '<text x="635" y="78" text-anchor="middle" fill="#a8b3c5" font-family="system-ui, sans-serif" font-size="16" letter-spacing="2">JORDAN</text>' +
          '<text class="jordan-upper" x="635" y="132" text-anchor="middle" fill="#2d9cff" font-family="system-ui, sans-serif" font-size="64" font-weight="700">' + esc(scene.jordanUpper) + "</text>" +
          '<g transform="translate(330 150)">' +
            '<circle cx="70" cy="48" r="40" fill="#f0c9a0" />' +
            '<path d="M36 36c10-30 64-30 70 4-22 6-50 8-70 0z" fill="#2a241c" />' +
            '<path d="M48 40h48" stroke="#2a241c" stroke-width="8" stroke-linecap="round" />' +
            '<circle cx="56" cy="54" r="3" fill="#1a140e" />' +
            '<circle cx="86" cy="54" r="3" fill="#1a140e" />' +
            '<path d="M60 72h22" stroke="#1a140e" stroke-width="3" stroke-linecap="round" />' +
            '<rect x="28" y="92" width="86" height="110" rx="8" fill="#1a2130" />' +
            '<rect x="58" y="92" width="26" height="110" fill="#f3f6fa" />' +
            '<path d="M62 118h18" stroke="#2d9cff" stroke-width="8" />' +
            '<circle cx="118" cy="150" r="8" fill="#2a3344" />' +
            '<rect x="112" y="158" width="6" height="40" fill="#2a3344" />' +
          "</g>" +
          '<rect x="180" y="360" width="440" height="28" rx="4" fill="#12171f" />' +
        "</svg>" +
      "</div>" +
      '<p class="bug"></p>' +
      '<div class="banner"><p class="flag">BREAKING</p><p class="crawl"></p></div>'
    );
  }

  var DRAW = {
    courtroom: courtroom,
    documentary: documentary,
    regulars: regulars,
    sports: sports,
  };

  function fillCourt(host, scene) {
    var words = String(scene.line || "").split(/\s+/).filter(Boolean);
    var h1 = host.querySelector("h1");
    words.forEach(function (word, index) {
      var span = document.createElement("span");
      span.className = "word";
      span.style.animationDelay = (index * 170) + "ms";
      span.textContent = word + (index < words.length - 1 ? " " : "");
      h1.appendChild(span);
    });
    host.style.setProperty("--bang", ((Math.max(words.length, 1) - 1) * 170) + "ms");
    var docket = host.querySelector(".docket");
    docket.appendChild(document.createTextNode((scene.label || "Box") + ". "));
    ["Erin", "Jordan"].forEach(function (name, index) {
      var value = index === 0 ? scene.erin : scene.jordan;
      var node = value === 0 ? document.createElement("b") : document.createElement("span");
      node.textContent = name + " " + value + ".";
      docket.appendChild(node);
      if (index === 0) docket.appendChild(document.createTextNode(" "));
    });
  }

  function fillRegulars(host, scene) {
    var chalk = host.querySelector(".chalk");
    var text = "Game " + (scene.gameSeq || "");
    if (scene.venue) text += " · " + scene.venue;
    if (scene.about === "yahtzee") text += " · Yahtzee 50";
    chalk.textContent = text;
  }

  function fillSports(host, scene, settled) {
    var bug = host.querySelector(".bug");
    var label = "Game " + (scene.gameSeq || "");
    if (scene.venue) label += " · " + scene.venue;
    bug.textContent = label;
    var crawl = host.querySelector(".crawl");
    var line = scene.line || "";
    if (settled) {
      crawl.textContent = line;
      return;
    }
    var index = 0;
    function tick() {
      if (!host.isConnected) return;
      index += 1;
      crawl.textContent = line.slice(0, index);
      if (index < line.length) setTimeout(tick, 18);
    }
    setTimeout(tick, 560);
  }

  function mount(host, scene, options) {
    options = options || {};
    scene = scene || {};
    var draw = DRAW[scene.cue] || courtroom;
    var settled = reducedMotion();
    host.className = "cutaway-layer" + (settled ? " is-settled" : "");
    host.dataset.scene = scene.cue || "courtroom";
    host.setAttribute("role", "dialog");
    host.setAttribute("aria-label", scene.line || "Cutaway");
    host.innerHTML = draw(scene);
    if (scene.cue === "courtroom") fillCourt(host, scene);
    if (scene.cue === "regulars") fillRegulars(host, scene);
    if (scene.cue === "sports") fillSports(host, scene, settled);
    var skip = document.createElement("button");
    skip.type = "button";
    skip.className = "skip";
    skip.textContent = "Skip";
    skip.addEventListener("click", function () {
      if (options.onSkip) options.onSkip();
    });
    host.appendChild(skip);
    return host;
  }

  return { mount: mount };
});
