"""charts.py — the two figures for post 1, rebuilt from data/derived/.

    python posts/01-fourth-downs/charts.py

Chart 1 (a, b): all 32 teams 2017-2025, dot + 90% interval, Bills highlighted.
Chart 2: Brady's cumulative WP cost per 4th down vs McDermott's per-down pace.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl

DERIVED = Path("data/derived")
OUT = Path("figures")

SURFACE, INK, INK_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#b5b4ad", "#e6e5e0"
BILLS = "#2a78d6"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
})


def league_dots(col: str, title: str, xlabel: str, interval_note: str, path: Path, pct: bool = False) -> None:
    """One row per team, sorted best (top) to worst, dot + 90% bar."""
    # row 0 sits at the bottom, so sort worst-first: high cost is bad, low go rate is bad
    df = pl.read_csv(DERIVED / "fourth_down_league.csv").sort(col, descending=not pct)
    scale = 100 if pct else 1
    fig, ax = plt.subplots(figsize=(6.4, 8.2))
    for i, r in enumerate(df.iter_rows(named=True)):
        is_buf = r["posteam"] == "BUF"
        color = BILLS if is_buf else MUTED
        ax.plot([r[f"{col}_lo"] * scale, r[f"{col}_hi"] * scale], [i, i], color=color, lw=2,
                solid_capstyle="round", zorder=2 + is_buf)
        ax.scatter(r[col] * scale, i, s=48 if is_buf else 30, color=color, edgecolor=SURFACE,
                   linewidth=2, zorder=3 + is_buf)
    ax.set_yticks(range(df.height), df["posteam"].to_list(), fontsize=8)
    for t in ax.get_yticklabels():
        if t.get_text() == "BUF":
            t.set_color(INK)
            t.set_fontweight("bold")
    ax.grid(axis="y", visible=False)
    ax.set_ylim(-0.8, df.height - 0.2)
    ax.set_xlabel(xlabel)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.005, f"2017–2025 regular season + playoffs. Bars: 90% {interval_note}. "
             "Data: nflverse, nfl4th.", fontsize=7, color=INK_2)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def brady_pace(path: Path) -> None:
    """Cumulative WP cost by 4th down, against McDermott's average cost per 4th down."""
    t = pl.read_csv(DERIVED / "brady_fourth_down_tracker.csv").with_row_index("n", offset=1)
    mcd = pl.read_csv(DERIVED / "fourth_down_eras.csv").filter(pl.col("era").str.starts_with("mcdermott"))
    pace = mcd["avg_wp_cost_pts"][0]
    n = t["n"].to_list()

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot([0, n[-1]], [0, pace * n[-1]], color=INK_2, lw=1.5, ls=(0, (4, 3)))
    ax.text(n[-1], pace * n[-1], f"  McDermott pace\n  ({pace:.2f}/4th down)", va="center", fontsize=8, color=INK_2)
    ax.step([0, *n], [0, *t["cum_wp_cost_pts"].to_list()], where="post", color=BILLS, lw=2)
    ax.text(n[-1], t["cum_wp_cost_pts"][-1], "  Brady", va="center", fontsize=9, color=INK, fontweight="bold")

    # week boundaries as quiet ticks along the bottom
    firsts = t.group_by("week").agg(pl.col("n").min(), pl.col("defteam").first()).sort("week")
    for i, (w, start, opp) in enumerate(firsts.iter_rows()):
        ax.axvline(start - 1, color=GRID, lw=0.8, zorder=0)
        ax.text(start - 0.6, -0.3 - 0.4 * (i % 2), f"Wk{w} {opp}", fontsize=7, color=INK_2, va="top")  # staggered: short weeks collide
    ax.grid(axis="x", visible=False)
    ax.set_xlim(0, n[-1] + 0.5)
    ax.set_ylim(-1.2, max(pace * n[-1], t["cum_wp_cost_pts"].max()) * 1.12)
    ax.set_xlabel("Brady's 4th downs, in order")
    ax.set_ylabel("Cumulative win probability given up (pts)")
    ax.set_title("Brady's fourth-down cost so far: one bad afternoon", loc="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.005, "WP cost = win probability of the nfl4th model's best call minus the call made. "
             "Data: nflverse, nfl4th.", fontsize=7, color=INK_2)
    fig.subplots_adjust(right=0.80, bottom=0.17)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    league_dots("avg_wp_cost_pts", "Win probability given up per 4th down", "WP pts per 4th down (lower is better)",
                "game-clustered bootstrap interval", OUT / "post1_chart1a_league_cost.png")
    league_dots("go_rate_on_go_calls", "Went for it when the model said go", "% of go-calls where the team went",
                "Wilson interval", OUT / "post1_chart1b_league_go_rate.png", pct=True)
    brady_pace(OUT / "post1_chart2_brady_pace.png")


if __name__ == "__main__":
    main()
