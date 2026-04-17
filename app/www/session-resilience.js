// Ping every 4min to keep the WebSocket alive past Cloud Run's 5min idle timeout.
// Pause when the tab isn't visible so forgotten tabs free their slot.
setInterval(function () {
  if (document.visibilityState !== "visible") return;
  if (window.Shiny && Shiny.setInputValue) {
    Shiny.setInputValue("_keepalive", Date.now(), { priority: "event" });
  }
}, 240000);

// If the WebSocket drops, reload instead of leaving the user on a dead page.
$(document).on("shiny:disconnected", function () {
  location.reload();
});
