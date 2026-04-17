console.log("[session-resilience] loaded");

// Ping every 4min to keep the WebSocket alive past Cloud Run's 5min idle timeout.
// Send directly through the socket so Shiny's input batching can't swallow it.
// Pause when the tab isn't visible so forgotten tabs free their slot.
setInterval(function () {
  if (document.visibilityState !== "visible") {
    console.log("[session-resilience] tab hidden, skip ping");
    return;
  }
  var sock = window.Shiny && Shiny.shinyapp && Shiny.shinyapp.$socket;
  if (sock && sock.readyState === 1) {
    sock.send(JSON.stringify({ method: "keepalive" }));
    console.log("[session-resilience] ping sent", new Date().toISOString());
  } else {
    console.warn("[session-resilience] socket not ready, skip ping");
  }
}, 240000);

// If the WebSocket drops, reload instead of leaving the user on a dead page.
$(document).on("shiny:disconnected", function (e) {
  console.warn("[session-resilience] disconnected, reloading", new Date().toISOString(), e);
  location.reload();
});
