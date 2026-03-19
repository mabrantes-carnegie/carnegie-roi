"""Number formatting helpers for the ROI dashboard."""


def fmt_number(n) -> str:
    """Format integer with comma separators. Returns '\u2014' for None/NaN."""
    if n is None or (isinstance(n, float) and (n != n)):
        return "\u2014"
    return f"{int(n):,}"


def fmt_pct(n) -> str:
    """Format as percentage with 1 decimal. Returns '\u2014' for None/NaN."""
    if n is None or (isinstance(n, float) and (n != n)):
        return "\u2014"
    return f"{n:.1f}%"


def fmt_currency(n) -> str:
    """Format as dollar amount. Returns '\u2014' for None/NaN."""
    if n is None or (isinstance(n, float) and (n != n)):
        return "\u2014"
    if abs(n) >= 1000:
        return f"${n:,.0f}"
    return f"${n:,.2f}"


def fmt_yoy(n) -> tuple[str, str]:
    """Format YoY change. Returns (display_string, sentiment).

    Sentiment: 'positive', 'negative', 'neutral', or 'na'.
    Format: "▲ X% vs. PY" or "▼ X% vs. PY" (whole percentages per spec).
    """
    if n is None or (isinstance(n, float) and (n != n)):
        return ("N/A", "na")
    rounded = round(n)
    if rounded > 0:
        return (f"\u25b2 {rounded}% vs. PY", "positive")
    elif rounded < 0:
        return (f"\u25bc {abs(rounded)}% vs. PY", "negative")
    else:
        return ("0% vs. PY", "neutral")
