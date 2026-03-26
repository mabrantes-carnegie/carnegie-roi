/**
 * Paginated tables — Carnegie ROI Dashboard
 * Adds pagination controls to any <table class="paginated-table">.
 * Works alongside sortable-tables.js (sort first, then paginate).
 * Re-applies on Shiny output updates via MutationObserver.
 */
(function () {
  "use strict";

  var PAGE_SIZE_OPTIONS = [10, 25, 50];

  function buildPaginator(table) {
    if (table._paginatorInit) return;
    table._paginatorInit = true;

    var tbody = table.querySelector("tbody");
    if (!tbody) return;

    // State
    var pageSize = PAGE_SIZE_OPTIONS[0];
    var currentPage = 1;

    function allRows() {
      return Array.from(tbody.querySelectorAll("tr"));
    }

    function totalPages() {
      return Math.max(1, Math.ceil(allRows().length / pageSize));
    }

    function render() {
      var rows = allRows();
      var total = rows.length;
      var pages = Math.max(1, Math.ceil(total / pageSize));
      if (currentPage > pages) currentPage = pages;

      var start = (currentPage - 1) * pageSize;
      var end = start + pageSize;

      rows.forEach(function (r, i) {
        r.style.display = (i >= start && i < end) ? "" : "none";
      });

      renderControls(total, pages);
    }

    // ── Controls container ──────────────────────────────────────
    var wrapper = table.closest(".paginated-table-wrapper");
    var ctrl = wrapper ? wrapper.querySelector(".pt-controls") : null;

    if (!ctrl) {
      wrapper = document.createElement("div");
      wrapper.className = "paginated-table-wrapper";
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);

      ctrl = document.createElement("div");
      ctrl.className = "pt-controls";
      ctrl.style.cssText = [
        "display:flex", "align-items:center", "justify-content:space-between",
        "padding:8px 4px 4px", "font-family:Manrope,sans-serif",
        "font-size:12px", "color:#6b7280", "flex-wrap:wrap", "gap:8px",
      ].join(";");
      wrapper.appendChild(ctrl);
    }

    function renderControls(total, pages) {
      ctrl.innerHTML = "";

      // Left: "Rows per page: [25▾]  |  1–25 of 312"
      var left = document.createElement("div");
      left.style.cssText = "display:flex;align-items:center;gap:12px;";

      var rppLabel = document.createElement("span");
      rppLabel.textContent = "Rows per page:";

      var sel = document.createElement("select");
      sel.style.cssText = [
        "font-family:Manrope,sans-serif", "font-size:12px", "color:#021326",
        "border:1px solid #e5e1dc", "border-radius:4px",
        "padding:2px 6px", "background:#fff", "cursor:pointer",
      ].join(";");
      PAGE_SIZE_OPTIONS.forEach(function (n) {
        var opt = document.createElement("option");
        opt.value = n;
        opt.textContent = n;
        if (n === pageSize) opt.selected = true;
        sel.appendChild(opt);
      });
      sel.addEventListener("change", function () {
        pageSize = parseInt(this.value, 10);
        currentPage = 1;
        render();
      });

      var rangeStart = (currentPage - 1) * pageSize + 1;
      var rangeEnd = Math.min(currentPage * pageSize, total);
      var info = document.createElement("span");
      info.textContent = rangeStart + "\u2013" + rangeEnd + " of " + total;

      left.appendChild(rppLabel);
      left.appendChild(sel);
      left.appendChild(info);

      // Right: [◀  1  2  3 … 12  ▶]
      var right = document.createElement("div");
      right.style.cssText = "display:flex;align-items:center;gap:4px;";

      function pageBtn(label, page, disabled, active) {
        var btn = document.createElement("button");
        btn.innerHTML = label;
        btn.style.cssText = [
          "font-family:Manrope,sans-serif", "font-size:12px",
          "border:1px solid " + (active ? "#EA332D" : "#e5e1dc"),
          "border-radius:4px", "padding:3px 9px",
          "background:" + (active ? "#EA332D" : "#fff"),
          "color:" + (active ? "#fff" : (disabled ? "#c0b8b0" : "#021326")),
          "cursor:" + (disabled ? "default" : "pointer"),
          "min-width:30px",
        ].join(";");
        if (!disabled && !active) {
          btn.addEventListener("click", function () {
            currentPage = page;
            render();
          });
        }
        return btn;
      }

      // Prev
      right.appendChild(pageBtn("&#8249;", currentPage - 1, currentPage === 1, false));

      // Page numbers with ellipsis
      var pagesToShow = [];
      if (pages <= 7) {
        for (var i = 1; i <= pages; i++) pagesToShow.push(i);
      } else {
        pagesToShow = [1];
        if (currentPage > 3) pagesToShow.push("…");
        for (var p = Math.max(2, currentPage - 1); p <= Math.min(pages - 1, currentPage + 1); p++) {
          pagesToShow.push(p);
        }
        if (currentPage < pages - 2) pagesToShow.push("…");
        pagesToShow.push(pages);
      }

      pagesToShow.forEach(function (p) {
        if (p === "…") {
          var sp = document.createElement("span");
          sp.textContent = "…";
          sp.style.cssText = "padding:0 4px;color:#6b7280;";
          right.appendChild(sp);
        } else {
          right.appendChild(pageBtn(p, p, false, p === currentPage));
        }
      });

      // Next
      right.appendChild(pageBtn("&#8250;", currentPage + 1, currentPage === pages, false));

      ctrl.appendChild(left);
      ctrl.appendChild(right);
    }

    // When sort happens, re-render (rows re-ordered in DOM)
    var sortObserver = new MutationObserver(function () {
      render();
    });
    sortObserver.observe(tbody, { childList: true });

    render();
  }

  function initAll() {
    document.querySelectorAll("table.paginated-table").forEach(buildPaginator);
  }

  document.addEventListener("DOMContentLoaded", initAll);

  if (typeof $ !== "undefined") {
    $(document).on("shiny:value", function () { setTimeout(initAll, 60); });
  }

  var observer = new MutationObserver(function (mutations) {
    var found = false;
    mutations.forEach(function (m) {
      m.addedNodes.forEach(function (n) {
        if (n.nodeType === 1 && (
          (n.tagName === "TABLE" && n.classList.contains("paginated-table")) ||
          (n.querySelector && n.querySelector("table.paginated-table"))
        )) { found = true; }
      });
    });
    if (found) setTimeout(initAll, 40);
  });
  observer.observe(document.body || document.documentElement, { childList: true, subtree: true });
})();
