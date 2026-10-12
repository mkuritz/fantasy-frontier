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

## Model
Stat-by-stat DK points: recency-weighted logs, blended with prop-line medians when posted. Scaled by Vegas implied total, defense vs position (shrunk 50%) and weather. Injury cascades push vacated targets and carries to healthy teammates. TDs and totals are regressed toward opportunity and salary-implied priors. Floor and ceiling are the 20th and 90th percentiles. DST uses the opponent's implied total on DK's points-allowed tiers, plus sack and takeaway rates.

## Optimizer
`assets/solver.js` (javascript-lp-solver, MIT) runs an exact integer program in the browser. It covers salary cap and min salary, classic slots, showdown CPT 1.5x, locks and excludes, max exposure, QB stack and bring-back, min unique players, and showdown game scripts. The contest type (cash, balanced, GPP) and entry-fee tier ($10/$20/$50/$100) set the risk profile. Lineups export as a DraftKings upload CSV. Local storage prefix: `ffx_`.

## Refresh
`.github/workflows/update.yml` runs a dispatcher (`scripts/dispatch.py`) every 30 min. It only rebuilds when new DK salaries post, about 2h and 45m before each lock, overnight around 3 AM ET, and on a 4-hourly daytime sweep. When a slate isn't posted yet, the last one stays up, labeled as the most recent available.

## Next
**NHL DFS is next.** It will reuse NHL Lab projections and goalie context with DraftKings NHL salaries.
