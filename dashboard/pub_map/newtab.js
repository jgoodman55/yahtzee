/* Retarget only the Top-tab pub map preview. Other /pub_map.html links stay.
   On a phone, let dashboard tables wrap so the scores stay on screen. */
(function () {
  function fitPhoneTables() {
    if (document.getElementById("phone-tables")) return;
    var style = document.createElement("style");
    style.id = "phone-tables";
    style.textContent = [
      "@media (max-width: 640px) {",
      "  table.w-full { min-width: 0 !important; width: 100% !important; }",
      "  table.w-full th, table.w-full td {",
      "    white-space: normal !important;",
      "    padding-left: 4px !important;",
      "    padding-right: 4px !important;",
      "    overflow-wrap: anywhere;",
      "    max-width: 11rem;",
      "  }",
      "  table.w-full th:first-child, table.w-full td:first-child {",
      "    white-space: nowrap !important;",
      "    max-width: 3.2rem;",
      "  }",
      "}"
    ].join("\n");
    (document.head || document.documentElement).appendChild(style);
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
    var observer = new MutationObserver(function (records) {
      records.forEach(function (record) {
        record.addedNodes.forEach(patch);
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
