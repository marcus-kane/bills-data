# Prediction log

Rules: write the prediction **before** running the analysis. Timestamp it.
Never edit a logged prediction — add a new entry instead. Score everything
in January, including the misses. Especially the misses.

Format:

```
## YYYY-MM-DD — <question>
**Prediction:** <specific, falsifiable>
**Confidence:** <low / medium / high>
**Why:** <one or two sentences — this is the part that's yours>
**Result:** (filled in later)
```

---

## 2026-09-22 23:53 CDT — Q1: stadium wind

**Prediction:** Two parts, both new Highmark 2026 home games vs Bills home games
at the old stadium 2016–2025, in percentage points:
1. Bills deep-ball success rate (air yards ≥ 20, success = EPA > 0) rises by
   0 to +5 pts.
2. Bills field-goal make rate rises by +1 to +3 pts.
**Confidence:** Medium on both.
**Why:** With a better offense this year I think Allen has more success on the
deep ball in a limited sample, and regardless, the evidence from this year's
small sample will point toward the stadium working. On kicking, I think the new
bowl may genuinely help late in the season when the weather turns, so I'll take
a chance on the FG rate going up a bit, even though it depends a lot on the
kicker.
**Result:**

## 2026-09-23 00:02 CDT — Q2: Brady vs McDermott on fourth down

*Logged late: the Phase 1 audit (including Brady's Weeks 1–2) ran on
2026-09-21, before this entry. This predicts the rest of the 2026 season.*

**Prediction:** On 4th downs where the nfl4th model's best call is "go," the
2026 Bills (Brady, head coach and play-caller) go for it at a higher rate
than the 2017–2025 Bills (McDermott), as of the end of the regular season.
**Confidence:** High
**Why:** Early in the season Brady has been aggressive and put the ball in his
best players' hands in the big moments. He's a modern coach who trusts the
numbers and trusts his QB, so he'll go for it when the numbers say go.
**Result:**

## 2026-09-23 00:08 CDT — Q3: Allen off-script

**Prediction:** Two parts, 2026 regular season vs Allen's 2022–2025, from
`src/off_script.py` (off-script = FTN out-of-pocket or scramble):
1. Allen's off-script rate goes up, but only barely: 0 to +3 pts.
2. His opponent-adjusted EPA per play on off-script dropbacks goes up.
**Confidence:** Medium
**Why:** Brady's scheme will let Josh be creative and use his legs: move the
pocket, slide protections, step up, run, and create plays more than he did
under McDermott. McDermott wanted to stay on schedule, leaned on screens and
tried to limit Josh's playmaking. Brady will embrace it. The rate barely
increases, but his success on broken-down plays goes up.
**Result:**

## 2026-09-23 00:08 CDT — Q4: defense vs schedule

*Logged late: the Phase 2 opponent adjustment (including 2026 season-to-date
ratings) ran on 2026-09-22, before this entry.*

**Prediction:** At the end of the 2026 regular season, the Bills' opponent-
adjusted defense (Leonhard) ranks within 5 spots of the 2025 Bills'
(McDermott's last season). How to read it:
- More than 5 spots better: that's the answer, Leonhard's defense is better.
- Within 5 spots: similar, and one season is too small a sample to say.
- More than 5 spots worse: cause for concern.
**Confidence:** Medium
**Why:** This defense is mostly players from McDermott's scheme. Leonhard has
hinted in his pressers that he has his scheme but not his perfect pieces yet.
Those players spent years in McDermott's 4-3, and Leonhard is bringing in a
lot of new scheme changes and roles. The defense only added talent and didn't
lose many key pieces from last year, so McDermott's defense should be the
floor for the defenses that come after it.
**Result:**
