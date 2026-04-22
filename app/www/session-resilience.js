// If the WebSocket drops, reload instead of leaving the user on a dead page.
$(document).on("shiny:disconnected", function () {
  location.reload();
});
