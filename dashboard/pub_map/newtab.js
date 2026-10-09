/* Retarget only the Top-tab pub map preview. Other /pub_map.html links stay.
   On a phone, only the comment column wraps. Winner, Erin, and Jordan
   stay on one line, and the score columns stay as wide as the numbers. */
(function () {
  function fitPhoneTables() {
    if (document.getElementById("phone-tables")) return;
    var style = document.createElement("style");
    style.id = "phone-tables";
    style.textContent = [
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
      "  table.w-full th.yahtzee-comment, table.w-full td.yahtzee-comment {",
      "    white-space: normal !important;",
      "    width: auto;",
      "    overflow-wrap: break-word;",
      "  }",
      "}"
    ].join("\n");
    (document.head || document.documentElement).appendChild(style);
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
      var commentIndex = -1;
      headers.forEach(function (th, index) {
        var label = (th.innerText || "").replace(/\s+/g, " ").toUpperCase();
        if (label.indexOf("COMMENT") !== -1) commentIndex = index;
      });
      if (commentIndex < 0) return;
      table.querySelectorAll("tr").forEach(function (row) {
        var cell = row.children[commentIndex];
        if (cell) cell.classList.add("yahtzee-comment");
      });
    });
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
