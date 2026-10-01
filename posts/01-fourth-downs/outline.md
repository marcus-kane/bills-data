# Post 1 — Fourth downs: the McDermott baseline, and Brady's first three games

Outline only. Prose is Marcus's. Numbers below are **through Week 3**
(refreshed 2026-10-01; Week 4 vs NE not yet played).

Target: ~800 words, 2 charts, 1 table. Ships this week.

---

## 1. Hook (1 paragraph)

- The question as logged: is Brady a better 4th-down decision maker than McDermott?
- Say up front what the post is and isn't: McDermott's full record is a real
  sample (n = 1,045). Brady's is 3 games. This post sets the baseline and starts
  the clock; it doesn't answer the question yet.
- Link to `predictions.md`. The Q2 prediction is public and timestamped, and says
  it was logged after Brady's Weeks 1–2 were run.

## 2. How the call gets graded (short, plain language)

- Baseline is the **nfl4th win-probability model** (Ben Baldwin, nflverse), not
  "EPA-optimal." For every 4th down it estimates win probability for go / punt /
  FG. The "right" call is the highest one.
- Two measures:
  - **% followed baseline**: did they make the model's call?
  - **WP cost**: when they didn't, how many win-probability points it cost on average.
- Q2's scored metric: **go rate when the model says go.** That's where coaches
  are timid, and it's the gap a modern coach should close.

## 3. What the model doesn't know (not a footnote; its own section)

- Injuries, the kicker that week, the wind at that moment, timeouts, personnel.
- Tie this to Buffalo: wind matters to punt vs FG in Orchard Park, and the model
  only sees one weather reading per game. That leads into the stadium study (Q1).
- Frame it as: "a call against the model" is a claim you can argue with, not a verdict.

## 4. The McDermott baseline (2017–2025)

- n = 1,045 fourth downs. Followed the model **73.1%** of the time.
  Average cost **0.30 WP pts** per 4th down.
- On the model's go-calls: went **162 of 400 = 40.5%** (90% CI 36.5–44.6%).
- **The league context flips the easy narrative.** 2017–2025, all 32 teams
  (`fourth_down_league.csv`):
  - Avg WP cost: Bills **5th-lowest** of 32 (0.30; 90% CI 0.26–0.34). League
    median 0.36. Best: CLE 0.26, worst: LAC 0.48.
  - Go rate on go-calls: Bills **12th** at 40.5%. League pooled 38.2%, range
    30% (SEA) to 49% (CLE).
  - So McDermott wasn't a timid 4th-down coach. He was a bit above average on
    going for it and near the top on not costing win probability. The bar for
    Brady is higher than "modern coach beats old-school coach." Say that plainly,
    since it cuts against the Q2 prediction's "Why."
  - Rank is soft: the Bills' cost interval overlaps most of the top half. Don't
    headline "5th." Headline "top-third, and statistically bunched with the pack."
- **Chart 1:** all 32 teams, avg WP cost as a dot + 90% bar, sorted, Bills
  highlighted. Second panel (or a follow-up chart): go rate on go-calls, same form.
- Football read (Marcus): where did McDermott leave value? Pick one or two famous
  punts/FGs from the tracker to make it concrete (search `decisions` for the
  biggest `wp_cost_pts`).

## 5. Brady so far

- Through Week 3: 12 fourth downs, followed the model 11/12 (91.7%), total
  WP cost 0.08 pts (avg 0.006/4th down vs McDermott's 0.30).
- Go-calls: went on **3 of 4** (75%). The 90% CI is **36%–94%**. McDermott's
  40.5% sits just above its low end, so Brady is ahead but not yet separated.
  Show that interval on purpose. It's the honest reason this post can't declare
  a winner.
- His one miss: Week 3 vs LAC, Q2, 4th & 9 at the LAC 10, down 10. Kicked the FG;
  the model said go. Cost: 0.08 WP pts, a near coin-flip call. Worth one honest
  line: the model's edge there is tiny, and kicking while down 10 to make it
  a one-score game is defensible on things the model can't see.
- Week 3, Q4, 4th & 6 at the 43, down 3: went, converted, EPA +4.4. The
  aggressive call that looks like the Brady the prediction bet on.
- Week 1 at HOU, 4th & 1 at the 34, Q1: went for it, EPA −4.2. The model said
  go and the model was right, even though the play failed. That's the teaching
  moment: grade the decision, not the result.
- **Chart 2:** Brady cumulative % followed / cumulative WP cost by week
  (`brady_fourth_down_tracker.csv`), with McDermott's era average as a flat
  reference line.

## 6. What would change my mind / what to watch

- How many go-calls before the interval means anything? McDermott saw ~2.4 per
  game (400 over 9 seasons). Brady has seen 4 in 3 games. At McDermott's pace
  that's ~40 by season's end, a 90% band of roughly ±13 pts. That's enough to
  separate "went 40%" from "went 70%", but not 40% from 50%. Say so, with the number.
- What would count as Brady being "the same as McDermott": say it now,
  before the data arrives.

## 7. Close

- One line on the cadence: this tracker updates every week, and so does the post.
- Tease post 2 (Allen off-script, or the stadium).

---

## Checklist before publish

- [ ] If Week 4 lands before publish: re-run the refresh + tracker and update section 5
- [ ] Both charts with intervals shown
- [ ] Every number traceable to a file in `data/derived/`
- [ ] Decide where it's hosted (Quarto → GitHub Pages as the default)
