(function () {
  function parseSelected(picker) {
    var raw = (picker.dataset.selected || "")
      .split(",")
      .map(function (item) { return item.trim(); })
      .filter(function (item) { return item.length > 0; });
    if (!raw.length) raw = ["clicks"];
    var maxItems = parseInt(picker.dataset.maxItems || "2", 10);
    if (!Number.isFinite(maxItems) || maxItems < 1) maxItems = 2;
    return raw.slice(0, maxItems);
  }

  function syncPicker(picker, notifyShiny) {
    var selected = parseSelected(picker);
    picker.dataset.selected = selected.join(",");

    picker.querySelectorAll(".metric-chip").forEach(function (chip) {
      var key = chip.dataset.key;
      var idx = selected.indexOf(key);
      var isActive = idx !== -1;
      var badge = chip.querySelector(".metric-chip-axis-badge");

      chip.classList.remove("is-active", "is-primary", "is-secondary");
      chip.setAttribute("aria-pressed", isActive ? "true" : "false");

      if (!badge) return;

      if (!isActive) {
        badge.textContent = "";
        return;
      }

      chip.classList.add("is-active");
      if (idx === 0) {
        chip.classList.add("is-primary");
        badge.textContent = "L";
      } else {
        chip.classList.add("is-secondary");
        badge.textContent = "R";
      }
    });

    if (notifyShiny && window.Shiny && typeof window.Shiny.setInputValue === "function") {
      window.Shiny.setInputValue(picker.dataset.inputId, selected, { priority: "event" });
    }
  }

  function toggleChip(chip) {
    var picker = chip.closest(".metric-chip-picker");
    if (!picker) return;

    var selected = parseSelected(picker);
    var maxItems = parseInt(picker.dataset.maxItems || "2", 10);
    if (!Number.isFinite(maxItems) || maxItems < 1) maxItems = 2;

    var key = chip.dataset.key;
    var idx = selected.indexOf(key);

    if (idx !== -1) {
      if (selected.length > 1) {
        selected = selected.filter(function (item) { return item !== key; });
      }
    } else if (selected.length >= maxItems) {
      selected = selected.slice(selected.length - maxItems + 1).concat([key]);
    } else {
      selected = selected.concat([key]);
    }

    picker.dataset.selected = selected.join(",");
    syncPicker(picker, true);
  }

  function syncAllPickers(notifyShiny) {
    document.querySelectorAll(".metric-chip-picker").forEach(function (picker) {
      syncPicker(picker, notifyShiny);
    });
  }

  document.addEventListener("click", function (event) {
    var chip = event.target.closest(".metric-chip");
    if (!chip) return;
    if (!chip.closest(".metric-chip-picker")) return;
    event.preventDefault();
    toggleChip(chip);
  });

  document.addEventListener("DOMContentLoaded", function () {
    syncAllPickers(false);
  });

  document.addEventListener("shiny:connected", function () {
    syncAllPickers(true);
  });
})();
