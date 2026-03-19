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
    """Format as dollar amount with 2 decimals. Returns '\u2014' for None/NaN."""
    if n is None or (isinstance(n, float) and (n != n)):
        return "\u2014"
    return f"${n:,.2f}"


def fmt_yoy(n) -> tuple[str, str]:
    """Format YoY change. Returns (display_string, sentiment).

    Sentiment: 'positive', 'negative', 'neutral', or 'na'.
    Used to select CSS badge class.
    """
    if n is None or (isinstance(n, float) and (n != n)):
        return ("N/A", "na")
    if n > 0:
        return (f"\u25b2 +{n:.1f}%", "positive")
    elif n < 0:
        return (f"\u25bc {n:.1f}%", "negative")
    else:
        return ("0.0%", "neutral")
