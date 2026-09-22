# Hand-charting codebook

*Write this before charting a single play.* The codebook is the deliverable —
it's what proves the dataset was created rather than downloaded.

## Scope

- **Variable being charted:** (undecided — wind direction relative to throw, or motion type)
- **Population:** which plays, which games, how selected
- **Target n:** 100

## Source of truth

- Film source and version
- What to do when the broadcast angle doesn't show the answer

## Variables

| Field | Type | Values | Definition | Edge cases |
|---|---|---|---|---|
| `play_id` | int | nflverse play_id | join key | — |
| | | | | |

## Decision rules

Every judgment call gets a rule here, written before charting, not after.

## Reliability

Re-chart a random 10% blind after a week. Report the agreement rate. If it's
below 90%, the definitions are too loose — tighten them and re-chart.

## Changelog

- 2026-09-21 — created
