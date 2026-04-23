"""Carnegie-branded error responses and inline banners.

Single source of truth for what users see when authentication or client
resolution fails. Used by:

- auth_middleware.py — full-page HTMLResponse for blocked requests
- server.py            — inline banner inside the Shiny layout when the
                        cookie expires mid-session
"""

from html import escape
from pathlib import Path

from starlette.responses import HTMLResponse

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "error.html"
_TEMPLATE = _TEMPLATE_PATH.read_text(encoding="utf-8")


def render_error_response(headline: str, message: str, status_code: int) -> HTMLResponse:
    """Render the Carnegie-branded error page as a Starlette HTMLResponse."""
    html = _TEMPLATE.format(
        headline=escape(headline),
        message=escape(message),
    )
    return HTMLResponse(html, status_code=status_code)


_BANNER_CSS = """
<style>
.carnegie-session-banner {
  position: fixed;
  inset: 0;
  z-index: 2147483647;
  background: #F8F4F0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  overflow-y: auto;
}
.carnegie-session-banner .card {
  background: #ffffff;
  border-left: 5px solid #EA332D;
  box-shadow: 0 6px 24px rgba(2, 19, 38, 0.08);
  border-radius: 6px;
  padding: 32px 40px;
  max-width: 460px;
  width: 100%;
  font-family: 'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  color: #021326;
}
.carnegie-session-banner .brand {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #EA332D;
  font-weight: 600;
  margin-bottom: 12px;
}
.carnegie-session-banner h2 {
  font-family: 'Lora', Georgia, serif;
  font-weight: 300;
  font-size: 26px;
  line-height: 1.25;
  margin: 0 0 14px 0;
  color: #021326;
}
.carnegie-session-banner p {
  font-size: 15px;
  line-height: 1.55;
  color: #4a5461;
  margin: 0;
}
</style>
"""


def render_banner_html(headline: str, message: str) -> str:
    """Return an inline HTML banner string, visually aligned with the error page.

    Safe to embed inside a Shiny ui.HTML(...) block.
    """
    return (
        f"{_BANNER_CSS}"
        f'<div class="carnegie-session-banner">'
        f'<div class="card" role="alert" aria-live="polite">'
        f'<div class="brand">Carnegie Funnel Report</div>'
        f"<h2>{escape(headline)}</h2>"
        f"<p>{escape(message)}</p>"
        f"</div></div>"
    )
