# Bills Data Project

*Working title — replace.*

Four questions about the 2026 Buffalo Bills, each with a falsifiable answer.

1. **Did the new Highmark Stadium actually cut the wind?**
   The architects claim field-level wind is reduced by roughly half to two-thirds
   versus the old stadium. Does that show up in deep-ball outcomes?
2. **Is Joe Brady a better fourth-down decision maker than Sean McDermott?**
   Every fourth down audited against an EPA-optimal baseline.
3. **Is Brady's design reducing Josh Allen's need to freelance?**
   Out-of-pocket rate and the efficiency gap between on-script and off-script plays.
4. **Is Jim Leonhard's defense actually better, or is the schedule easier?**
   An opponent adjustment, validated out-of-sample.

Question 4 is infrastructure for the other three.

---

## Status

| Phase | What | State |
|---|---|---|
| 0 | Spine: data pull, cache, DuckDB, `refresh.py` | done |
| 1 | Fourth-down audit | done — live weekly tracker |
| 2 | Opponent adjustment | done — validated out-of-sample |
| 3 | Allen off-script | built — awaiting Q3 prediction before first run |
| 4 | Stadium wind study (capstone) | weather pipeline live (Bills home games) |
| 5 | Publish | not started |

## Repo layout

```
data/raw/      parquet cache, one dir per source (gitignored)
data/db/       bills.duckdb (gitignored)
data/derived/  committed output tables (e.g. the weekly 4th-down tracker)
src/           analysis modules
notebooks/     exploration only — nothing ships from here
charting/      hand-charted data + codebook (this is the differentiator)
posts/         weekly writeups
figures/       generated charts (gitignored)
docs/          plan of action, methodology notes
refresh.py         re-pull current season, rebuild the db
weekly_tracker.py  regenerate every weekly table (Q2-Q4) in data/derived/
predictions.md timestamped predictions, logged BEFORE the numbers are run
```

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python refresh.py --full
```

## Ground rules

- Predictions go in `predictions.md` with a timestamp **before** the analysis runs.
- Every claim about a coach's decision names what the model doesn't know.
- No point estimates without an interval.
- Hand-charted data ships with its codebook.

## Sources

- [FTN charting dictionary](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html)
- [Next Gen Stats dictionary](https://nflreadr.nflverse.com/articles/dictionary_nextgen_stats.html)
- [nflverse data update schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html)
- [nflreadr load_participation](https://nflreadr.nflverse.com/reference/load_participation.html)
- [nfl4th load_4th_pbp](https://www.nfl4th.com/reference/load_4th_pbp.html)
- [NFL Weather Data is Lying to You](https://thespade.substack.com/p/nfl-weather-data-is-lying-to-you)
- [Bills stadium designed to reduce wind](https://sports.yahoo.com/articles/bills-stadium-designed-reduce-wind-100121390.html)
- [The design of Buffalo's Highmark Stadium](https://www.forbes.com/sites/timnewcomb/2026/07/30/the-design-of-buffalos-highmark-stadium-heating-up-the-bills-mafia/)
