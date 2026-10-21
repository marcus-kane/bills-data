"""charts.py — the figure for post 2, rebuilt from data/derived/.

    python posts/02-off-script/charts.py

Allen's EPA/dropback on- and off-script by play-caller era, dot + 90% bar.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl

DERIVED = Path("data/derived")
OUT = Path("figures")

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
OFF, ON = "#2a78d6", "#eb6834"  # categorical slots 1-2

ERAS = [  # top to bottom, oldest first
    ("dorsey_oc", "Dorsey OC\n2022–Wk 10 2023"),
    ("brady_oc", "Brady OC\nWk 11 2023–2025"),
    ("brady_hc", "Brady HC\n2026"),
]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
})


def era_chart(path: Path) -> None:
    df = pl.read_csv(DERIVED / "allen_off_script_eras.csv")
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for i, (era, _) in enumerate(ERAS):
        y = len(ERAS) - 1 - i
        rows = {r["stat"]: r for r in df.filter(pl.col("era") == era).iter_rows(named=True)}
        for stat, color, dy, filled in (("epa_off", OFF, 0.12, True), ("epa_on", ON, -0.12, False)):
            r = rows[stat]
            ax.plot([r["lo"], r["hi"]], [y + dy] * 2, color=color, lw=2, solid_capstyle="round")
            ax.scatter(r["value"], y + dy, s=56, zorder=3, linewidth=2,
                       color=color if filled else SURFACE, edgecolor=color)
        gap = rows["gap"]
        ax.text(1.0, y, f"gap {gap['value']:+.2f}\n({gap['lo']:+.2f} to {gap['hi']:+.2f})\n{gap['games']} games",
                va="center", fontsize=8, color=INK_2)

    # direct labels on the 2026 row, where the two series are furthest apart
    hc = {r["stat"]: r for r in df.filter(pl.col("era") == "brady_hc").iter_rows(named=True)}
    ax.text(hc["epa_off"]["value"], 0.12 + 0.17, "off-script", ha="center", fontsize=8, color=INK)
    ax.text(hc["epa_on"]["value"], -0.12 - 0.17, "on-script", ha="center", va="top", fontsize=8, color=INK)

    ax.axvline(0, color=INK_2, lw=0.8)
    ax.set_yticks(range(len(ERAS)), [label for _, label in reversed(ERAS)], fontsize=9)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(-0.15, 1.0)
    ax.set_ylim(-0.6, len(ERAS) - 0.4)
    ax.set_xlabel("Opponent-adjusted EPA per dropback")
    ax.set_title("Allen off-script: never better, never less certain", loc="left", fontsize=12, fontweight="bold")
    ax.legend(handles=[
        plt.Line2D([], [], color=OFF, marker="o", lw=2, markersize=7, label="Off-script (out of pocket or scramble)"),
        plt.Line2D([], [], color=ON, marker="o", markerfacecolor=SURFACE, lw=2, markersize=7, label="On-script"),
    ], loc="upper left", bbox_to_anchor=(0, -0.2), ncol=2, frameon=False, fontsize=8)
    fig.text(0.01, 0.005, "Regular season, win prob 5–95%. Bars: 90% game-clustered bootstrap; optimistic below "
             "~10 games. Data: nflverse, FTN.", fontsize=7, color=INK_2)
    fig.subplots_adjust(left=0.2, right=0.83, top=0.9, bottom=0.3)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    era_chart(OUT / "post2_chart_off_script_eras.png")


if __name__ == "__main__":
    main()
