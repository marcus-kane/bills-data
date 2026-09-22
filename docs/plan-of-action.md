# Bills Data Project — Plan of Action

Owner: Marcus Kane · Started Sept 21, 2026 (Week 3 of the 2026 season)

Working title placeholder: **Pinning the Buffalo** — replace with something of your own.

---

## The four questions

Each project is stated as a question with a falsifiable answer, not a topic.

1. **Did the new Highmark Stadium actually cut the wind?** The architects claim field-level wind is reduced by roughly half to two-thirds versus the old stadium. Test whether that shows up in deep-ball outcomes.
2. **Is Joe Brady a better fourth-down decision maker than Sean McDermott?** Audit every fourth down against an EPA-optimal baseline.
3. **Is Brady's design reducing Josh Allen's need to freelance?** Measure out-of-pocket rate and the efficiency gap between on-script and off-script plays.
4. **Is Jim Leonhard's defense actually better, or is the schedule easier?** Build an opponent adjustment and find out.

Project 4 is infrastructure for the other three. Build it second, use it everywhere.

---

## Data inventory — what exists

| Source | Granularity | Years | In-season updates |
|---|---|---|---|
| nflverse play-by-play | per play, ~380 cols | 1999+ | nightly |
| FTN charting | **per play** | 2022+ | 4×/day |
| Next Gen Stats | player-week **aggregate** | 2016+ | nightly |
| Snap counts, PFR advanced | player-game | 2012+ | 4×/day |
| Participation (personnel, coverage, man/zone) | per play | 2016+ | **postseason only** |
| nfl4th precomputed decisions | per 4th down | 2014+ | with pbp |
| Schedules, rosters, depth charts, injuries | game/player | — | daily |

**FTN is the sleeper.** Per-play flags for motion, play action, QB out of pocket, screen, RPO, no huddle, QB alignment (under center / shotgun / pistol), blitzer count, pass rusher count, read thrown, interception-worthy, throwaway, catchable ball, contested ball, drop. Updated in season. This is what carries projects 2 and 3.

---

## The data holes, per project

### 1. Stadium wind

- **pbp weather is one reading per game**, frequently missing, taken from the nearest airport station. The new Highmark is among the furthest NFL stadiums from any weather station.
- **No wind direction relative to field orientation.** Field is roughly north–south; you need the azimuth and a way to convert station wind bearing into cross/head/tail wind.
- **No on-field anemometer data, publicly or privately.** The 50–67% reduction claim comes from CFD modeling, not measurement. You cannot verify the engineering — only whether the football outcomes moved.
- **n ≈ 9–10 home games this season.** You cannot fit a stadium-specific wind response curve from that.

**Workarounds:** interpolate hourly weather per play with the `meteostat` Python package (METAR + ISD-Lite), giving three or four readings per game instead of one. Fit the wind → deep-ball-outcome curve on *all* outdoor stadiums, 2016–2025, then treat new Highmark 2026 as an out-of-sample test with honest uncertainty bands. Report the interval, not a point estimate.

### 2. Fourth down

- **`nfl4th` is R-only.** Either run that one step in R, or read the precomputed decisions the package hosts (`load_4th_pbp(fast = TRUE)`, 2014+) straight from the nflverse release as parquet and do everything else in Python.
- **The model doesn't know what the coach knew:** injuries, that week's kicker, the wind at that moment, timeout state, personnel availability. Every "the coach was wrong" claim is contestable, and saying so is part of doing it well.
- **No record of who made the call** or of sideline constraints.
- **n for Brady is 2 games.** The shippable version is a full historical audit plus a live tracker that fills in.

### 3. Allen off-script

- **NGS time-to-throw is a weekly average, not per play.** "EPA when he holds it 3+ seconds" is not publicly computable. This kills the original framing.
- **Substitute, and a better one:** FTN `is_qb_out_of_pocket` per play, 2022+, plus `qb_scramble` from pbp, `read_thrown`, `n_pass_rushers`, `is_throwaway`. Out-of-pocket is a cleaner definition of off-script than a time threshold anyway.
- **No pressure timing, no pocket-collapse duration, no pre-snap defensive look.**
- **FTN starts in 2022,** so four seasons. Fine for Allen's prime, not for a career arc.

### 4. Opponent adjustment

Not a data hole — a methodology hole, which is harder.

- Circular early in the season: everyone's rating depends on everyone else's.
- Needs regularization toward a league-mean prior, or week-1 ratings are noise.
- Garbage-time filtering and QB-availability adjustment are judgment calls you must document.
- **No ground truth to validate against.** The only honest validation is out-of-sample: does adjusted EPA predict next week's result better than raw EPA? Run that test and report the number. This is the step that separates the project from a blog post.

---

## What makes it yours

The analysis is the commodity. These are not.

**Chart 100 plays by hand.** Pick one variable public data doesn't have and build it yourself — wind direction relative to the throw on every Bills deep attempt, or the specific motion types Brady uses that FTN collapses into a single binary flag. Write a codebook first. Publish the codebook with the data. This proves you can *create* a dataset, not just download one, and it is the single strongest signal in the whole project.

**Write your predictions down before you run the numbers.** Commit them to the repo with a timestamp. You know this team; use that as hypothesis generation, then report every place you were wrong. Almost nobody does this and it reads as unmistakably honest.

**Test someone's public claim.** The stadium project has a spine because the architects said a number out loud. Find the actual quote, cite it, and check it. A project that adjudicates a real claim beats a project that describes a trend.

**Write like a person.** Every piece gets a short interpretation in your own voice — what it means for the team, what you'd tell a fan at the bar. Keep the football writing and the statistics in the same document.

**Ship weekly.** A short post after each game. Ten of those by January is a body of work; one notebook is an afternoon. The cadence is the credential.

**Put it in front of people who will argue with you.** TwoBillsDrive, r/buffalobills, Buffalo beat writers, the nflverse Discord. Take the criticism, cite it, publish a v2. A documented feedback loop is the thing interviewers ask about.

---

## Phased build

### Phase 0 — This week: the spine

- Python 3.12 in a venv; `nfl_data_py`, `polars`, `duckdb`, `meteostat`, `matplotlib`, plus `quarto` for the site.
- R installed for the one `nfl4th` step, or the precomputed parquet read directly.
- Pull and cache: pbp 2016–2026, FTN 2022–2026, NGS weekly, snap counts, PFR advanced, schedules, injuries. Land as parquet in `data/raw/`, then load into a single DuckDB file.
- Write `refresh.py` that re-pulls only the current season. **This is the difference between a project and a notebook.**
- Git repo. README that states the four questions up front, before any chart.
- Commit the prediction log, empty except your four predictions.

### Phase 1 — Weeks 1–2: fourth-down audit

Easiest win, ships fastest, builds momentum. Full McDermott era against the baseline, benchmarked against all 32 teams, then a live Brady tracker that updates weekly.

### Phase 2 — Weeks 2–4: opponent adjustment

Build it because the other three need it. Ridge regression on team-vs-team EPA with a league-mean prior. Include the out-of-sample validation test.

### Phase 3 — Weeks 4–7: Allen off-script

FTN out-of-pocket rate and the on-script/off-script efficiency gap, 2022–2026, with the league distribution for context.

### Phase 4 — Weeks 5 through season's end: the stadium study

Stand up the meteostat pipeline early so it accumulates automatically. Write it up after the final home game. **This is the capstone** — it's the one nobody else can have done first.

### Phase 5 — January: publish

Long-form writeup, the site, the prediction scorecard, outreach.

---

## Deliverables by February

- A public GitHub repo with a working refresh pipeline
- A live dashboard that updates weekly
- Four or five short written pieces
- One long capstone on the stadium
- A hand-charted dataset with a published codebook
- A scored prediction log

---

## Open decisions

- Project name and whether it lives on its own domain
- Whether the hand-charting variable is wind direction or motion type
- Whether to do the whole thing in Python with an R shim, or accept R for the modeling steps

---

## Sources

- [FTN charting dictionary](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html)
- [Next Gen Stats dictionary](https://nflreadr.nflverse.com/articles/dictionary_nextgen_stats.html)
- [nflverse data update schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html)
- [nflreadr load_participation](https://nflreadr.nflverse.com/reference/load_participation.html)
- [nfl4th load_4th_pbp](https://www.nfl4th.com/reference/load_4th_pbp.html)
- [NFL Weather Data is Lying to You](https://thespade.substack.com/p/nfl-weather-data-is-lying-to-you)
- [Bills stadium designed to reduce wind](https://sports.yahoo.com/articles/bills-stadium-designed-reduce-wind-100121390.html)
- [The design of Buffalo's Highmark Stadium](https://www.forbes.com/sites/timnewcomb/2026/07/30/the-design-of-buffalos-highmark-stadium-heating-up-the-bills-mafia/)
