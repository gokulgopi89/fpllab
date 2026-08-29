# fpllab

Pulls the FPL API and Understat, joins them, and projects expected points per player per gameweek. Runs entirely on your machine — no keys, no accounts, no data leaving the box except the two GET requests.

## Setup

```bash
cd fpl-lab
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run it

```bash
# rank every player over the next 5 gameweeks
python -m fpllab.cli project --gws 5

# your squad: best XI, captain, weak links, upgrades
python -m fpllab.cli squad --file my_squad.txt --rebuild

# best legal 15 from scratch at £100m
python -m fpllab.cli optimise --budget 100 --gws 5

# fixture difficulty as expected goals, not FDR
python -m fpllab.cli fixtures --gws 6

# the dashboard
streamlit run app.py        # http://localhost:8501
```

`my_squad.txt` is pre-filled with your auto-pick. Edit and re-run.

First run takes a couple of minutes (it fetches ~260 player histories). Everything is cached for 6 hours in `~/.fpllab/cache`; `--fresh` bypasses it, `clear-cache` empties it.

## Where the numbers come from

| Source | Endpoint | What it gives |
|---|---|---|
| FPL | `bootstrap-static/` | prices, positions, ownership, injury status, team strength ratings |
| FPL | `fixtures/` | schedule, FDR, blanks and doubles |
| FPL | `element-summary/{id}/` | per-GW history, previous-season totals, BPS, defensive contributions |
| Understat | `league/EPL/{season}` | npxG, xA, shots, key passes, and per-match team xG/xGA |

Understat has no API — the data is embedded in the page as escaped JSON and `understat.py` unpacks it. If they change the page layout, that's the one file that breaks.

## How the projection works

**1. Player rates.** npxG and xA per 90 from Understat, blended across the current and previous season by minutes played (last season discounted to 55%), then shrunk toward the positional mean with a 420-minute prior. That shrinkage is what stops a striker with 180 minutes and two tap-ins from topping the table.

**2. Expected minutes.** Current-season minutes per gameweek and last season's minutes-per-appearance, weighted by how much current-season evidence exists, then multiplied by availability from `status` and `chance_of_playing_next_round`.

**3. Fixture difficulty.** Not FDR. Each team gets home and away attack/defence indices from Understat match history, blended 65/35 with FPL's own strength ratings — the FPL side is what covers newly promoted clubs with no Premier League xG. Expected goals for a fixture are `league_average × your_attack × their_defence`, plus home advantage.

**4. Points.** Appearance + goals × positional value + assists × 3 + clean sheet × `P(opponent scores 0)` from a Poisson + goals-conceded deductions + GK saves + defensive-contribution probability + a bonus proxy from BPS per 90. Clean sheets and defcon are scaled by the probability of reaching 60 minutes.

**5. Selection.** Exact integer programme via PuLP: maximise projected points subject to £100m, 2/5/5/3, and max 3 per club. Best XI searches all legal formations and doubles the top scorer for the captaincy.

## Tuning it

Every assumption is a field in `fpllab/config.py`. Dump a copy and edit:

```python
from fpllab.config import Config
Config().save("config.json")
```

Then `python -m fpllab.cli project --config config.json`. The ones worth arguing about:

- `prior_season_weight` — raise it early in the season, drop toward 0.2 by GW10
- `shrinkage_minutes` — higher is more conservative about small samples
- `strength_blend_understat` — lower it in August when this season's xG barely exists
- `goal_points`, `clean_sheet_points`, `defcon_points` — **check these against the current rules before trusting any output.** They're set for the scoring system as I understand it, and FPL has changed scoring between seasons.

## Known limits

- **Name matching** is team-constrained, then fuzzy. It resolves most of the league; run with `-v` to see what didn't match. Unmatched players fall back to positional means and get flagged `confidence: low`.
- **Promoted clubs and new signings** have no Premier League xG. They lean on FPL strength ratings and show low confidence. Treat their projections as priors, not predictions.
- **Set-piece and penalty duties** come from `penalties_order`, which is often empty in preseason. Check them manually for anyone you're paying up for.
- **No price-change or ownership modelling**, no chip strategy, no multi-week transfer planning. Single-swap suggestions only.
- The bonus proxy is a linear fit on BPS per 90, not a simulation of the BPS race. It's directionally right and individually noisy.

Projections are a starting point for your own judgement, not a substitute for it. The model doesn't know a manager said something in a press conference this morning.
