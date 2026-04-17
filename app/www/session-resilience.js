console.log("[session-resilience] loaded");

// Ping every 4min to keep the WebSocket alive past Cloud Run's 5min idle timeout.
// Pause when the tab isn't visible so forgotten tabs free their slot.
setInterval(function () {
  if (document.visibilityState !== "visible") {
    console.log("[session-resilience] tab hidden, skip ping");
    return;
  }
  if (window.Shiny && Shiny.setInputValue) {
    Shiny.setInputValue("_keepalive", Date.now(), { priority: "event" });
    console.log("[session-resilience] ping sent", new Date().toISOString());
  } else {
    console.warn("[session-resilience] Shiny not ready, skip ping");
  }
}, 240000);

// If the WebSocket drops, reload instead of leaving the user on a dead page.
$(document).on("shiny:disconnected", function (e) {
  console.warn("[session-resilience] disconnected, reloading", new Date().toISOString(), e);
  location.reload();
});
