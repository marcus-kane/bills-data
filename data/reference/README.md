# Reference data

## stadiums.csv

Stadium coordinates, altitude (m) and field heading (bearing of the field's
long axis, degrees) keyed on the Pro Football Reference stadium ID that
nflverse uses (`BUF00`, `KAN00`, ...).

- Source: [greerreNFL/Stadiums](https://github.com/greerreNFL/Stadiums),
  `data/stadiums.csv` at commit `79739e5` (2026-09-15). Location fields were
  set by hand in Google Earth by that repo's author. Only these columns are
  kept here.
- Heading convention checked on 2026-09-23 against fields known to run
  north–south: Soldier Field 356°, Lambeau 359°, Mile High 0°, Lumen 0°.
- **`BUF00` is the old Highmark** (42.7738, -78.7870, heading 302°). The new
  Highmark (2026+) shares the ID in nflverse but is a different field. Its
  heading lives in `src/weather.py` as `NEW_HIGHMARK_HEADING` and is unset
  until measured.
