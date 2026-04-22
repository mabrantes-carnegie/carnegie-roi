"""Client-neutral dashboard constants."""

import pandas as pd


# Academic month ordering (Jul=1 ... Jun=12)
ACAD_ORDER = {
    7: 1, 8: 2, 9: 3, 10: 4, 11: 5, 12: 6,
    1: 7, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12,
}
MONTH_LABELS = {
    1: "Jul", 2: "Aug", 3: "Sep", 4: "Oct", 5: "Nov", 6: "Dec",
    7: "Jan", 8: "Feb", 9: "Mar", 10: "Apr", 11: "May", 12: "Jun",
}


# Goals were previously loaded from a bundled CSV, which can represent a
# specific client. Leave them empty until a client-parameterized source exists.
GOALS: dict[str, int] = {}
PROGRAM_GOALS = pd.DataFrame(
    columns=[
        "program",
        "goal_inquiries",
        "goal_app_starts",
        "goal_app_submits",
        "goal_admits",
        "goal_deposits",
        "goal_net_deposits",
        "program_lower",
    ]
)
