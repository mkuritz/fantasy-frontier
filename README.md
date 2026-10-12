# Fantasy Frontier · NFL DFS Lab (Beta)

A Sports Labs product. DraftKings NFL daily fantasy research: stat-based projections, value plays, chalk vs leverage, recommended lineups and a client-side lineup optimizer for the **Thursday Night (showdown)**, **Sunday main (classic)** and **Monday Night (showdown)** slates.

Live: https://mkuritz.github.io/fantasy-frontier/

## Data (all free)
| What | Source | Real or estimated |
|---|---|---|
| Salaries, positions, CPT/FLEX ids | DraftKings public lobby (`lobby/getcontests`) + salary CSV export (`lineup/getavailableplayerscsv`) | Real |
| Game logs, usage, defense vs position | nflverse weekly player stats | Real |
| Spreads, totals, implied team totals | ESPN (DraftKings lines) | Real |
| Injury statuses | ESPN | Real |
| Weather at kickoff | Open-Meteo | Forecast |
| Player prop lines, anytime-TD model | Bet Lab (`mkuritz/bet-lab`) data files | Real lines, modeled TD odds |
| Projections (mean/floor/ceiling), ownership proxy, edges | `scripts/fetch_dfs.py` | **Estimates** |

`api.draftkings.com/draftgroups/.../draftables` is blocked (403) from datacenter IPs, so the salary CSV export is used instead (same data).

## Model (v2: usage × efficiency, Monte Carlo)
- **This season only, recency-weighted:** snap % (nflverse snap counts), target share, carry share, and red-zone target and carry share (nflverse play-by-play). The last game weighs 32%, then 24%, 17%, 12%, and so on. An expanding-role flag fires when opportunity share jumps 35% or more, or snaps rise 18+ points, over the last 2 games.
- **Role filter:** a player needs 35%+ snaps, a 10%+ target share or a 25%+ carry share, and must have been active recently. Backup QBs, low-role players and players ruled out are left out of recommendations. Showdown DSTs are faded when the total is 49 or higher.
- **Injury redistribution:** only the share an out player actually held recently is vacated. It's split proportionally across healthy teammates, adjusted by with/without splits when the player already missed games, and same-position teammates get 55% priority.
- **News:** ESPN team news (athlete-tagged, last 6 days) and injury notes are scanned for role language. This nudges usage by ±7–8% and shows up in the edge notes.
- **Game script:** team volume comes from the team's own pace × (Vegas total)^0.35–0.45, with underdogs throwing more and favorites running more. TDs come from the implied team total (≈0.118 TDs per point), split pass/rush by the team's TD mix and allocated by red-zone and overall share. Bet Lab anytime-TD odds are blended in 50/50, capped at 115% of the team's TD budget. QBs are anchored to their own recent passing.
- **Matchup:** this season's defense vs position (DK points allowed, shrunk 60%) adjusts efficiency. Player-vs-opponent history (this season and last) appears as an edge note.
- **Monte Carlo:** 4,000 sims per game. A shared game factor lifts both teams in a shootout, and multinomial target and carry splits mean QB and pass-catchers covary. Mean, floor (20th percentile) and ceiling (90th) come from the sims. 160 sims per player ship to the browser for GPP lineups and captain rankings.
- `scripts/sanity.py` prints the top projections by position, top values, captain rankings and spot checks.

## Optimizer
`assets/solver.js` (javascript-lp-solver, MIT) runs an exact integer program in the browser. It covers salary cap and min salary, classic slots, showdown CPT 1.5x, locks and excludes, max exposure, QB stack and bring-back, min unique players, and showdown game scripts. The contest type (cash, balanced, GPP) and entry-fee tier ($10/$20/$50/$100) set the risk profile. Lineups export as a DraftKings upload CSV. Local storage prefix: `ffx_`.

## Refresh
`.github/workflows/update.yml` runs a dispatcher (`scripts/dispatch.py`) every 30 min. It only rebuilds when new DK salaries post, about 2h and 45m before each lock, overnight around 3 AM ET, and on a 4-hourly daytime sweep. When a slate isn't posted yet, the last one stays up, labeled as the most recent available.

## Next
**NHL DFS is next.** It will reuse NHL Lab projections and goalie context with DraftKings NHL salaries.

## Model v3 (phase 2)
- **Cross-referenced sources:** usage-model sim (estimate) blended 30/70 with Sleeper/RotoWire projections (external). The table shows how much the sources agree, plus FantasyCalc rank and Sleeper trending adds. Big disagreements are flagged.
- **News:** ESPN team news plus RotoWire and CBS RSS, matched to players.
- **Backtest (weeks 3–5):** results in `data/backtest.json`, shown on the How it works page. Sleeper alone has a lower MAE than our model alone. We keep a 30% model weight for game correlation and news/injury cascades, and the UI says so.
- **"Their shot":** opportunity-spike edge plays. When a player's role expands, we weight his elevated-role history and with/without splits.
- **Rest of season:** weekly ROS projections (estimate) from neutral baseline × opponent DvP × implied total.
- **Charts:** salary-budget donut, distribution, this season vs last season, and usage trends with z-tests.
