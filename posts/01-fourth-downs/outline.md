# Post 1 — Fourth downs: the McDermott baseline, and Brady's first four games

Outline only. Prose is Marcus's. Numbers below are **through Week 6**
(refreshed 2026-10-20: 37–34 OT win at LA, 33–30 win at LV).

Target: ~800 words, 2 charts, 1 table. Ships this week.

---

## 1. Hook (1 paragraph)

- The question as logged: is Brady a better 4th-down decision maker than McDermott?
- Say up front what the post is and isn't: McDermott's full record is a real
  sample (n = 1,045). Brady's is 6 games. This post sets the baseline and starts
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
- **Chart 1:** `figures/post1_chart1a_league_cost.png` (avg WP cost, 90%
  bootstrap bar) and `figures/post1_chart1b_league_go_rate.png` (go rate on
  go-calls, 90% Wilson bar). Both sorted best-on-top, Bills highlighted.
  Rebuild with `python posts/01-fourth-downs/charts.py`.
- Football read (Marcus): where did McDermott leave value? Pick one or two famous
  punts/FGs from the tracker to make it concrete (search `decisions` for the
  biggest `wp_cost_pts`).

## 5. Brady so far

- Through Week 6: 27 fourth downs, followed the model 22/27 (81.5%), total
  WP cost 4.31 pts (avg 0.16/4th down vs McDermott's 0.30).
- Go-calls: went on **4 of 9** (44.4%). The 90% CI is **22%–70%**. McDermott's
  40.5% sits in the middle of it, so there is no separation at all yet.
- **The West Coast trip didn't test him.** 9 fourth downs at LA and LV, 9 of 9
  with the model, 0.00 WP cost. But all 9 were punts or FGs the model also
  wanted: zero go-calls in two games. A clean two weeks is not evidence of
  aggressiveness; it's the absence of a test. Say that, or a reader will.
  Show that interval on purpose. It's the honest reason this post can't declare
  a winner.
- **The NE game is the story.** Through Week 3 he was 11/12 with the model, 3 of
  4 on go-calls, 0.08 WP pts of total cost. Then one afternoon: 6 fourth downs,
  5 go-calls, went once, **4.23 WP pts** given away in a 3-point loss.
  - Q1, 4th & 2 at the NE 41, down 7: went, converted, EPA +2.9. The only go.
  - Q2, 4th & 3 at his own 37, tied: punted. Cost 1.13.
  - Q3, 4th & 7 at his own 44, down 4: punted. Cost 0.85.
  - Q3, 4th & 4 at his own 17, down 4: punted. Cost 1.80, the biggest of his
    season, and the call almost no coach makes. Argue with the model here
    (section 3), don't just report it.
  - Q4, 4th & 10 at the NE 20, down 4: kicked the FG. Cost 0.46.
- Wind that day was 18–22 km/h, the windiest game of Week 4. The model saw one
  weather reading. Worth a line, and it's the bridge to Q1.
- His one miss before NE: Week 3 vs LAC, Q2, 4th & 9 at the LAC 10, down 10.
  Kicked the FG; the model said go. Cost: 0.08 WP pts, a near coin-flip call.
- Week 3, Q4, 4th & 6 at the 43, down 3: went, converted, EPA +4.4. The
  aggressive call that looks like the Brady the prediction bet on.
- Week 1 at HOU, 4th & 1 at the 34, Q1: went for it, EPA −4.2. The model said
  go and the model was right, even though the play failed. That's the teaching
  moment: grade the decision, not the result.
- **Chart 2:** `figures/post1_chart2_brady_pace.png`. Brady's cumulative WP
  cost per 4th down vs McDermott's pace (0.30 × downs). The NE staircase is
  the chart, and so is the flat line after it.

## 6. What would change my mind / what to watch

- How many go-calls before the interval means anything? McDermott saw ~2.5 per
  game (400 in 163 games). Brady has seen 9 in 6 games (1.5/game, and none in
  Weeks 5–6). At that pace it's ~25 by season's end, a 90% band of roughly
  ±16 pts. That separates "went 40%" from "went 75%" and nothing finer. Q2 may
  not be answerable from 2026 alone. Say so, with the number.
- What would count as Brady being "the same as McDermott": say it now,
  before the data arrives.

## 7. Close

- One line on the cadence: this tracker updates every week, and so does the post.
- Tease post 2 (Allen off-script, or the stadium).

---

## Checklist before publish

- [x] Week 4 landed: refresh + tracker re-run, section 5 updated (2026-10-06)
- [x] Week 6 landed: section 5 + section 6 updated (2026-10-20)
- [x] Both charts with intervals shown (`posts/01-fourth-downs/charts.py`)
- [ ] Every number traceable to a file in `data/derived/`
- [ ] Decide where it's hosted (Quarto → GitHub Pages as the default)
