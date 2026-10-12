/* Retarget only the Top-tab pub map preview. Other /pub_map.html links stay.
   The comment and what-decided-it columns wrap on word boundaries. On a
   phone those two sit on their own lines, and Winner, Erin, and Jordan
   stay on one line with the game number. Watch replay is its own line. */
(function () {
  function fitPhoneTables() {
    if (document.getElementById("phone-tables")) return;
    var style = document.createElement("style");
    style.id = "phone-tables";
    style.textContent = [
      "table.w-full th.yahtzee-comment, table.w-full td.yahtzee-comment,",
      "table.w-full th.yahtzee-story, table.w-full td.yahtzee-story {",
      "  white-space: normal;",
      "  overflow-wrap: break-word;",
      "  vertical-align: top;",
      "}",
      "table.w-full th.yahtzee-comment, table.w-full td.yahtzee-comment { max-width: 16rem; }",
      "table.w-full th.yahtzee-story, table.w-full td.yahtzee-story { max-width: 28rem; }",
      "@media (max-width: 640px) {",
      "  table.w-full { min-width: 0 !important; width: 100% !important; }",
      "  table.w-full th, table.w-full td {",
      "    white-space: nowrap !important;",
      "    padding-left: 4px !important;",
      "    padding-right: 4px !important;",
      "    width: 1%;",
      "  }",
      "  table.w-full thead button {",
      "    padding-left: 4px !important;",
      "    padding-right: 4px !important;",
      "    letter-spacing: 0 !important;",
      "    gap: 0 !important;",
      "  }",
      "  table.w-full thead button span[aria-hidden='true'] { display: none !important; }",
      "  table.w-full th.yahtzee-comment, table.w-full td.yahtzee-comment,",
      "  table.w-full th.yahtzee-story, table.w-full td.yahtzee-story {",
      "    white-space: normal !important;",
      "    width: auto;",
      "    overflow-wrap: break-word;",
      "  }",
      "  table.yahtzee-story-table { display: block; }",
      "  table.yahtzee-story-table thead { display: none; }",
      "  table.yahtzee-story-table tbody { display: block; }",
      "  table.yahtzee-story-table tr {",
      "    display: flex;",
      "    flex-wrap: wrap;",
      "    align-items: baseline;",
      "    column-gap: 10px;",
      "    row-gap: 4px;",
      "    padding: 12px 16px 14px;",
      "    border-bottom: 1px solid var(--dac-border, #2a3344);",
      "  }",
      "  table.yahtzee-story-table td {",
      "    display: inline-flex;",
      "    align-items: baseline;",
      "    gap: 4px;",
      "    width: auto !important;",
      "    white-space: nowrap !important;",
      "    padding: 0 !important;",
      "  }",
      "  table.yahtzee-story-table td.yahtzee-comment,",
      "  table.yahtzee-story-table td.yahtzee-story {",
      "    display: block;",
      "    flex: 1 0 100%;",
      "    width: 100% !important;",
      "    max-width: none !important;",
      "    white-space: normal !important;",
      "    line-height: 1.35;",
      "  }",
      "  table.yahtzee-story-table td[data-col]::before {",
      "    content: attr(data-col);",
      "    font-size: 0.68rem;",
      "    letter-spacing: 0.03em;",
      "    opacity: 0.6;",
      "  }",
      "  table.yahtzee-story-table td[data-col='Game'] { order: 1; }",
      "  table.yahtzee-story-table td[data-col='Winner'] { order: 2; }",
      "  table.yahtzee-story-table td[data-col='Erin'] { order: 3; }",
      "  table.yahtzee-story-table td[data-col='Jordan'] { order: 4; }",
      "  table.yahtzee-story-table td.yahtzee-comment { order: 5; }",
      "  table.yahtzee-story-table td.yahtzee-story { order: 6; }",
      "  table.yahtzee-story-table td.yahtzee-replay {",
      "    order: 7;",
      "    flex: 1 0 100%;",
      "    width: 100% !important;",
      "    white-space: normal !important;",
      "  }",
      "}"
    ].join("\n");
    (document.head || document.documentElement).appendChild(style);
  }

  function headerLabel(th) {
    return (th.innerText || "").replace(/[▲▼]/g, " ").replace(/\s+/g, " ").trim().toUpperCase();
  }

  function chipLabel(label) {
    if (label.indexOf("GAME") === 0) return "Game";
    if (label.indexOf("WINNER") !== -1) return "Winner";
    if (label.indexOf("ERIN") === 0) return "Erin";
    if (label.indexOf("JORDAN") === 0) return "Jordan";
    return "";
  }

  function markCommentColumn(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var tables = [];
    if (scope.tagName === "TABLE") tables.push(scope);
    if (scope.querySelectorAll) {
      scope.querySelectorAll("table").forEach(function (table) {
        tables.push(table);
      });
    }
    tables.forEach(function (table) {
      var headers = table.querySelectorAll("thead th");
      var labels = [];
      var hasComment = false;
      var hasStory = false;
      headers.forEach(function (th, index) {
        var label = headerLabel(th);
        labels[index] = label;
        if (label.indexOf("COMMENT") !== -1) hasComment = true;
        if (label.indexOf("DECIDED") !== -1) hasStory = true;
      });
      if (!hasComment && !hasStory) return;
      if (hasStory) table.classList.add("yahtzee-story-table");
      table.querySelectorAll("tr").forEach(function (row) {
        Array.prototype.forEach.call(row.children, function (cell, index) {
          var label = labels[index] || "";
          if (label.indexOf("COMMENT") !== -1) cell.classList.add("yahtzee-comment");
          if (label.indexOf("DECIDED") !== -1) cell.classList.add("yahtzee-story");
          if (label.indexOf("REPLAY") !== -1) {
            cell.classList.add("yahtzee-replay");
            if (cell.tagName === "TD") linkReplay(cell, row, labels);
          }
          var chip = chipLabel(label);
          if (hasStory && cell.tagName === "TD" && chip) cell.setAttribute("data-col", chip);
        });
      });
    });
  }

  function linkReplay(cell, row, labels) {
    if (cell.querySelector("a")) return;
    var gameIndex = -1;
    labels.forEach(function (label, index) {
      if (label.indexOf("GAME") === 0) gameIndex = index;
    });
    var gameCell = gameIndex >= 0 ? row.children[gameIndex] : null;
    var gameNo = gameCell ? String(gameCell.textContent || "").replace(/\D/g, "") : "";
    if (!/^\d+$/.test(gameNo)) return;
    var link = document.createElement("a");
    link.href = "/scorecards/viewer.html?game=" + gameNo + "&replay=1#replay";
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "Watch replay";
    cell.textContent = "";
    cell.appendChild(link);
  }

  function pathOf(value) {
    try {
      return new URL(value, location.origin).pathname;
    } catch (e) {
      return String(value || "");
    }
  }

  function isPreviewLink(anchor) {
    if (!anchor || anchor.tagName !== "A") return false;
    if (pathOf(anchor.getAttribute("href") || "") !== "/pub_map.html") return false;
    var img = anchor.querySelector("img");
    if (!img) return false;
    var src = img.getAttribute("src") || "";
    return src.indexOf("/pub_map/preview.") !== -1;
  }

  function patch(root) {
    if (!root || root.nodeType !== 1) return;
    var anchors = [];
    if (root.tagName === "A") anchors.push(root);
    if (root.querySelectorAll) {
      root.querySelectorAll("a").forEach(function (anchor) {
        anchors.push(anchor);
      });
    }
    anchors.forEach(function (anchor) {
      if (!isPreviewLink(anchor)) return;
      anchor.target = "_blank";
      anchor.rel = "noopener";
    });
  }

  function start() {
    fitPhoneTables();
    patch(document.body || document.documentElement);
    markCommentColumn(document);
    var observer = new MutationObserver(function (records) {
      records.forEach(function (record) {
        record.addedNodes.forEach(function (node) {
          patch(node);
          markCommentColumn(node);
        });
      });
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
