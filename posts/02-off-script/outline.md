# Post 2 — Allen off-script: what the West Coast trip says about Q3

Outline only. Prose is Marcus's. Numbers **through Week 6** (refreshed
2026-10-20). Source: `data/derived/allen_off_script_eras.csv` unless noted.
Era EPA is opponent-adjusted (`epa_adj`); per-game numbers are raw EPA.

Target: ~700 words, 1 chart, 1 table. Ships week of Oct 26 (Week 7 is the bye).

---

## 1. Hook: SoFi, Monday night

- Allen at LA: **8 scrambles, 107 yards, +11.7 EPA** on scrambles alone.
  That's more scramble EPA in one night than in Weeks 1–4 combined (+10.0).
- His arm that night was ordinary: −1.4 CPOE, 0.37 EPA per pass.
  The legs won it: 21-yard scramble to the LA 5 at 2:00 of the 4th (set up
  Cook's TD), 19-yard scramble in OT (set up Bass's 45-yard winner).
- Then the twist: at LV six days later, **1 scramble, 2 yards**. Shortest aDOT
  of the season (6.4), +5.7 CPOE, 35 dropbacks. A completely different QB game.
- Question: which one is Brady's design, and which one is Allen bailing it out?

## 2. What "off-script" means here (short)

- FTN `is_qb_out_of_pocket` OR a scramble. Per play, charted by FTN, 2022+.
- Games under 95% charted are dropped whole. All 6 of 2026's pass.
- Split by **play-caller**, not by head coach: Dorsey OC (2022–Wk 10 2023),
  Brady OC (Wk 11 2023–2025), Brady HC (2026). "2022–25 vs 2026" would credit
  Brady's own play-calling to McDermott.
- League-relative rate (`off_rate_vs_league`), because FTN's league-wide
  out-of-pocket rate drifts up year to year.

## 3. The table

| Era | Off-script rate vs league | EPA on-script | EPA off-script | Gap |
|---|---|---|---|---|
| Dorsey OC (26 g) | +3.2 pts (1.2 to 5.5) | 0.16 | 0.35 | 0.19 (−0.02 to 0.41) |
| Brady OC (39 g) | +5.0 pts (3.0 to 7.2) | 0.18 | 0.23 | 0.05 (−0.11 to 0.21) |
| Brady HC (6 g) | +10.3 pts (2.5 to 19.1) | 0.17 | **0.63** | **0.46 (0.10 to 0.82)** |

90% game-clustered bootstrap intervals.

- The read: under Brady-as-HC, Allen leaves the pocket more than ever
  (raw 29.9%), and when he does he's been devastating. On-script efficiency
  hasn't moved (0.17 vs 0.18).
- The gap's interval excludes zero, and so does the change vs Brady OC
  (+0.41, 0.03 to 0.78). **But:** CLAUDE.md rule, and say it in the post:
  bootstrap bands are optimistic below ~10 games. Six games, 197 dropbacks.

## 4. Per-game, so nobody thinks it's smooth

Allen off-script rate and EPA, raw, by game (from `load_dropbacks`):

| Wk | Opp | Off-script rate | EPA off | EPA on |
|---|---|---|---|---|
| 1 | @HOU | 21% | 0.57 | 0.50 |
| 2 | DET | 44% | 0.32 | 0.63 |
| 3 | LAC | 16% | 0.58 | −0.25 |
| 4 | NE | 19% | 0.34 | 0.01 |
| 5 | @LA | 48% | 0.90 | 0.50 |
| 6 | @LV | 32% | 1.05 | −0.07 |

- Two of the three highest-rate games came on the road, in domes. Don't
  claim a dome effect off two games. Do note it as something to watch.
- LV is the strangest line: 32% off-script with only 1 scramble, so it's
  out-of-pocket *throws*, and on-script he was below zero. That's a
  football question for the film, not the spreadsheet: was the pocket
  collapsing (Allen was sacked twice), or
  was it called rollouts?

## 5. Score the prediction honestly (as logged 2026-09-23)

- Part 1: "rate goes up, barely, 0 to +3 pts." Right now, league-adjusted, it's
  **+5.3 pts vs Brady OC (−2.9 to +14.1)**. Point estimate is above the
  predicted band; the interval still covers it. Say "trending against me."
- Part 2: "off-script EPA goes up." **+0.41 (0.12 to 0.67).** Trending right.
- No edits to `predictions.md`. Score in January.

## 6. What the model doesn't know

- FTN's out-of-pocket flag doesn't separate designed rollouts and bootlegs
  from broken plays. "Off-script" overstates freelancing on a bootleg-heavy
  day. This is the hand-charting variable question (open decision in
  CLAUDE.md): motion type / designed movement would fix exactly this.
- No time-to-throw per play exists publicly. Don't imply it.
- Opponents so far rank 12th–29th in adjusted defense; the adjustment handles
  some of it, not all of it.

## 7. Close

- What would change my mind: if on-script EPA stays flat and the off-script
  gap shrinks toward Brady-OC's 0.05 by Week 12, the SoFi game was Allen
  being Allen, not Brady's design.
- Tease post 3: the new stadium's first three games (Q1).

**Chart:** off-script EPA by era, dot + 90% bar, three rows, with the
on-script value as a hollow marker on the same row. One axis (EPA/play).

---

## Checklist before publish

- [x] Chart: `figures/post2_chart_off_script_eras.png`, rebuilt by `python posts/02-off-script/charts.py`
- [ ] Week 8 (BAL, Nov 1) refresh if it slips past the bye
- [ ] Film check on LV out-of-pocket plays (designed vs broken)
- [ ] Every number traceable to `data/derived/` or a function in `src/`
