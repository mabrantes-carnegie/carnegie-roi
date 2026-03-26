/**
 * Sortable tables — Carnegie ROI Dashboard
 * Adds click-to-sort on any <table class="sortable-table">.
 * Numeric strings (with commas/%, +/- signs) sort numerically.
 * Re-applies on Shiny output updates via MutationObserver.
 */
(function () {
  "use strict";

  function parseNum(str) {
    if (typeof str !== "string") return NaN;
    var s = str.replace(/,/g, "").replace(/%/g, "").replace(/^\+/, "").trim();
    if (s === "—" || s === "N/A" || s === "") return NaN;
    return parseFloat(s);
  }

  function getCellValue(row, idx) {
    var cell = row.cells[idx];
    return cell ? (cell.textContent || cell.innerText || "").trim() : "";
  }

  function compareValues(a, b, asc) {
    var na = parseNum(a), nb = parseNum(b);
    var result;
    if (!isNaN(na) && !isNaN(nb)) {
      result = na - nb;
    } else {
      result = a.toLowerCase().localeCompare(b.toLowerCase());
    }
    return asc ? result : -result;
  }

  function initTable(table) {
    if (table._sortableInit) return;
    table._sortableInit = true;
    table.classList.add("sortable-table");

    var headers = table.querySelectorAll("thead th");
    headers.forEach(function (th, idx) {
      th.style.cursor = "pointer";
      th.style.userSelect = "none";
      th._sortAsc = null; // null = unsorted, true = asc, false = desc

      th.addEventListener("click", function () {
        var asc = th._sortAsc !== true; // toggle; first click = asc
        // Reset other headers
        headers.forEach(function (h) {
          h._sortAsc = null;
          h.setAttribute("data-sort", "");
        });
        th._sortAsc = asc;
        th.setAttribute("data-sort", asc ? "asc" : "desc");

        var tbody = table.querySelector("tbody");
        if (!tbody) return;
        var rows = Array.from(tbody.querySelectorAll("tr"));
        rows.sort(function (a, b) {
          return compareValues(getCellValue(a, idx), getCellValue(b, idx), asc);
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      });
    });
  }

  function initAll() {
    document.querySelectorAll("table.sortable-table").forEach(initTable);
  }

  // Initial run after DOM ready
  document.addEventListener("DOMContentLoaded", initAll);

  // Re-run when Shiny updates outputs
  if (typeof $ !== "undefined") {
    $(document).on("shiny:value", function () {
      setTimeout(initAll, 50);
    });
  }

  // MutationObserver fallback for dynamic content
  var observer = new MutationObserver(function (mutations) {
    var found = false;
    mutations.forEach(function (m) {
      m.addedNodes.forEach(function (n) {
        if (n.nodeType === 1 && (n.tagName === "TABLE" || n.querySelector && n.querySelector("table.sortable-table"))) {
          found = true;
        }
      });
    });
    if (found) setTimeout(initAll, 30);
  });
  observer.observe(document.body || document.documentElement, { childList: true, subtree: true });
})();
