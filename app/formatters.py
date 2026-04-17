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


def fmt_compact(n) -> str:
    """Format a count as a whole number, using M/B suffix for large values.

    Examples: 397 → '397', 1250 → '1,250', 1_500_000 → '1.5M', 2_000_000 → '2M',
              1_250_000_000 → '1.3B', 3_000_000_000 → '3B'.
    """
    if n is None or (isinstance(n, float) and n != n):
        return "\u2014"
    n = round(n)
    if abs(n) >= 1_000_000_000:
        v = n / 1_000_000_000
        s = f"{v:.1f}B"
        return s[:-2] + "B" if s.endswith(".0B") else s
    if abs(n) >= 1_000_000:
        v = n / 1_000_000
        s = f"{v:.1f}M"
        return s[:-2] + "M" if s.endswith(".0M") else s
    return f"{n:,}"


def resolve_line_label_layout(
    series_list,
    chart_height=320,
    min_gap_px=18,
    base_yshift_px=14,
    step_yshift_px=12,
    max_stacks=8,
):
    """Resolve line-label placement for multi-series line charts.

    Parameters
    ----------
    series_list : list[dict]
        Each dict should include:
        - series_idx: int
        - xs: iterable of x values
        - ys: iterable of y values
        - texts: iterable of pre-formatted label strings
    chart_height : int
        Approximate chart height in pixels, used to estimate rendered proximity.
    min_gap_px : int
        Minimum readable vertical gap between label centers at the same x.
    base_yshift_px : int
        Initial pixel offset from the point for the first label in a stack.
    step_yshift_px : int
        Additional pixel offset applied as the stack grows.
    max_stacks : int
        Maximum number of stack levels to attempt before suppressing.

    Returns
    -------
    dict
        {series_idx: {x_val: {"show": bool, "yshift": int, "xshift": int, "position": str}}}
    """
    import math

    def _is_valid_num(v):
        return v is not None and not (isinstance(v, float) and math.isnan(v))

    def _unique_key(v):
        if hasattr(v, "isoformat"):
            try:
                return v.isoformat()
            except Exception:
                return str(v)
        return str(v)

    def _x_sort_key(v):
        if hasattr(v, "toordinal"):
            try:
                return ("dt", v.toordinal())
            except Exception:
                pass
        return ("obj", str(v))

    def _x_numeric(v, mapping):
        if hasattr(v, "toordinal"):
            try:
                return float(v.toordinal())
            except Exception:
                pass
        return float(mapping[_unique_key(v)])

    def _stack_offsets():
        offsets = []
        for level in range(max_stacks):
            mag = base_yshift_px + ((level // 2) * step_yshift_px)
            sign = 1 if level % 2 == 0 else -1
            offsets.append(sign * mag)
        return offsets

    all_y = []
    all_x = []
    points = []
    for series in series_list:
        s_idx = series["series_idx"]
        xs = list(series["xs"])
        ys = list(series["ys"])
        texts = list(series["texts"])
        default_pos = series.get("default_pos", "top center")
        for x_val, y_val, text in zip(xs, ys, texts):
            if not _is_valid_num(y_val) or not text:
                continue
            all_y.append(float(y_val))
            all_x.append(x_val)
            points.append({
                "series_idx": s_idx,
                "x": x_val,
                "y": float(y_val),
                "text": text or "",
                "default_pos": default_pos,
            })

    if not points:
        return {}

    unique_x = sorted({_unique_key(x): x for x in all_x}.values(), key=_x_sort_key)
    x_mapping = {_unique_key(x): i for i, x in enumerate(unique_x)}
    y_min = min(all_y)
    y_max = max(all_y)
    y_range = max(y_max - y_min, 1.0)
    result = {}
    plot_height_px = max(chart_height - 90, 120)
    px_per_y = plot_height_px / y_range if y_range else 1.0
    offsets = _stack_offsets()

    by_x = {}
    for point in points:
        by_x.setdefault(point["x"], []).append(point)

    for x_val, x_points in by_x.items():
        x_points = sorted(x_points, key=lambda p: (-p["y"], p["series_idx"]))
        placed_centers = []
        for rank, point in enumerate(x_points):
            point_px = (point["y"] - y_min) * px_per_y
            # Highest point prefers above; next prefers below; then expand outward.
            preferred = offsets[:]
            if rank % 2 == 1:
                preferred = preferred[1:2] + preferred[0:1] + preferred[2:]
            chosen = None
            for yshift in preferred:
                label_center = point_px + yshift
                if all(abs(label_center - other_center) >= min_gap_px for other_center in placed_centers):
                    chosen = yshift
                    break
            show = chosen is not None
            if not show:
                result.setdefault(point["series_idx"], {})[x_val] = {
                    "show": False,
                    "yshift": 0,
                    "xshift": 0,
                    "position": "middle center",
                }
                continue
            placed_centers.append(point_px + chosen)
            result.setdefault(point["series_idx"], {})[x_val] = {
                "show": True,
                "yshift": int(chosen),
                "xshift": 0,
                "position": "middle center",
            }

    return result


def resolve_line_label_positions(series_list, suppress_pct=0.03):
    """Backward-compatible wrapper for legacy textposition callers."""
    layout = resolve_line_label_layout(series_list)
    result = {}
    for s_idx, point_map in layout.items():
        for x_val, spec in point_map.items():
            pos = "top center" if spec["yshift"] >= 0 else "bottom center"
            result.setdefault(s_idx, {})[x_val] = (pos, spec["show"])
    return result


def resolve_label_collisions(series_points_map, suppress_pct=0.03):
    """Assign per-point textposition and visibility to reduce label overlap.

    Parameters
    ----------
    series_points_map : dict
        {x_val: [(y_val, series_idx), ...]} — all series data grouped by x position.
    suppress_pct : float
        Suppress a label if its y value is within this fraction of the total y-range
        from an already-placed label at the same x. Set to 0 to never suppress.

    Returns
    -------
    dict  {series_idx: {x_val: (position_str, show_bool)}}

    Usage
    -----
    smap = {}
    for x, y in zip(xs_a, ys_a): smap.setdefault(x, []).append((y, 0))
    for x, y in zip(xs_b, ys_b): smap.setdefault(x, []).append((y, 1))
    lbl = resolve_label_collisions(smap)
    pos_a = [lbl.get(0, {}).get(x, ("top center", True))[0] for x in xs_a]
    txt_a = [fmt(y) if lbl.get(0, {}).get(x, (None, True))[1] else "" for x, y in zip(xs_a, ys_a)]
    """
    series_list = []
    series_vals = {}
    for x_val, pts in series_points_map.items():
        for y_val, s_idx in pts:
            bucket = series_vals.setdefault(s_idx, {"xs": [], "ys": [], "texts": []})
            bucket["xs"].append(x_val)
            bucket["ys"].append(y_val)
            bucket["texts"].append(str(y_val) if y_val is not None else "")
    for s_idx, vals in series_vals.items():
        series_list.append({
            "series_idx": s_idx,
            "xs": vals["xs"],
            "ys": vals["ys"],
            "texts": vals["texts"],
            "default_pos": "top center" if s_idx % 2 == 0 else "bottom center",
        })
    return resolve_line_label_positions(series_list, suppress_pct=suppress_pct)


def fmt_yoy(n) -> tuple[str, str]:
    """Format YoY change. Returns (display_string, sentiment).

    Sentiment: 'positive', 'negative', 'neutral', or 'na'.
    Format: "▲ X% vs. YoY" or "▼ X% vs. YoY" (whole percentages per spec).
    """
    if n is None or (isinstance(n, float) and (n != n)):
        return ("N/A", "na")
    rounded = round(n)
    if rounded > 0:
        return (f"\u25b2 {rounded}% YoY", "positive")
    elif rounded < 0:
        return (f"\u25bc {abs(rounded)}% YoY", "negative")
    else:
        return ("0% YoY", "neutral")
