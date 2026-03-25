# ═══════════════════════════════════════════════════════════
# CARNEGIE DESIGN SYSTEM — REFERENCE BLOCK v1.0
# Source: Carnegie Corporate Color Palette + Type System PDF
# Use this block in every Carnegie project prompt.
# ═══════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────
COLORS — USE HEX IN ALL DIGITAL / DASHBOARD WORK
────────────────────────────────────────────────────────────

PRIMARY (these three define Carnegie — always lead with them):

  Carnegie Red      #EA332D    Primary accent, CTAs, active states
  Carnegie Blue     #021326    Primary text, headings, dark backgrounds
  Off White         #F8F4F0    Page backgrounds, breathing room

SECONDARY (use for charts, infographics, supporting elements only):

  Carnegie Gold     #C99D44    Warmth, polish — limited use

  Light Red         #FFDBD9
  Dark Red          #560422

  Light Blue        #A4B9D3
  Dark Blue         #021326

  Light Orange      #FBCFB1
  Dark Orange       #370C05

  Light Purple      #E9DBF6
  Dark Purple       #41334E

  Light Green       #B3C7BD
  Dark Green        #132B23

  Light Yellow      #FFF8B4
  Dark Yellow       #543F00   (use with extreme care)

COLOR USAGE RULES:
  - Secondary colors are for charts and infographics only.
  - Never assign meaning to colors (e.g., no "green = enrollment").
  - Never assign colors to departments or services.
  - Primary colors must dominate; secondary colors support.
  - Maintain WCAG AA contrast: 4.5:1 for normal text, 3:1 for large text (18pt+).
  - Carnegie Red and Carnegie Blue have strong contrast on Off White.
  - Always test color combinations before implementation.

────────────────────────────────────────────────────────────
TYPOGRAPHY — THREE FONTS, STRICT SCOPE
────────────────────────────────────────────────────────────

FONT 1 — Lora  (Google Fonts — no installation needed)
  Usage:       Headlines and dashboard titles ONLY
  Weights by role:
    Headline Large (H1):   Lora Thin (weight 100),  line-height: 100%
    Headline Small (H2):   Lora Light (weight 300),  line-height: 115%
    Subheadline (H3):      Lora Light (weight 300),  line-height: 115%
    Pull Quotes:           Lora Light (weight 300),  line-height: 120%
  Google Fonts import:
    "family=Lora:wght@100;300;400"

FONT 2 — Manrope  (Google Fonts — no installation needed)
  Usage:       ALL other text without exception
               (body, UI labels, filters, cards, tables,
                tooltips, tab names, axis labels, footnotes)
  Weights by role:
    Body Text:    Manrope Regular (weight 400), line-height: 140%
    Information:  Manrope Medium (weight 500),  line-height: 140%
    UI / Nav:     Manrope Bold (weight 700),    uppercase, letter-spacing: 0.07813rem
  Google Fonts import:
    "family=Manrope:wght@400;500;600;700"

FONT 3 — Inter  (Google Fonts — no installation needed)
  Usage:       Numeric values inside charts and data visualizations ONLY
               (axis tick labels, data point labels, hover values in Plotly)
  Google Fonts import:
    "family=Inter:wght@400;500"

COMBINED GOOGLE FONTS IMPORT (use this single URL for all three):
  https://fonts.googleapis.com/css2?family=Lora:wght@100;300;400&family=Manrope:wght@400;500;600;700&family=Inter:wght@400;500&display=swap

TYPOGRAPHY SCALE (maintain 200% minimum size difference between
headlines and body copy):
  Example base 12pt: headlines at 24pt, 30pt, 36pt+

FONT SMOOTHING (apply globally):
  -webkit-font-smoothing: antialiased;

────────────────────────────────────────────────────────────
APPLICATION RULES FOR DASHBOARDS
────────────────────────────────────────────────────────────

  - Dashboard/page titles:      Lora Thin (100), line-height 100%
  - Section headings:           Lora Light (300), line-height 115%
  - All labels, tabs, filters:  Manrope Bold (700), uppercase
  - Card values / body text:    Manrope Regular (400) or Medium (500)
  - Chart numeric labels:       Inter Regular (400)
  - Background:                 Off White #F8F4F0
  - Primary text:               Carnegie Blue #021324
  - Active/accent elements:     Carnegie Red #FA3320
  - Secondary chart colors:     use secondary palette in order,
                                 never assign semantic meaning to color
