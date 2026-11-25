# MUET Point (Bus) System – Discrete Event Simulation

Modeling, simulation and scheduling optimization of the MUET Point (bus) system using queueing theory and
discrete event simulation (Python / SimPy). Compares a static timetable with zone-based dispatch.

**Author:** Tayyaba Bhatti (Roll No. 051) – PBL Assignment, Modeling and Simulation
Mehran University of Engineering and Technology, Jamshoro

## Problem

In the afternoon peak, students at the STC and Main Gate terminals wait long for a Point. This project models the
system, finds the bottleneck and tests whether assigning buses to dedicated terminals reduces waiting time
without adding buses.

## Policies compared (14 buses, capacity 45)

| ID  | Policy                                                                |
| --- | --------------------------------------------------------------------- |
| P0  | Static timetable: a bus every 4 min, visits STC then Main Gate        |
| P1  | Zone-based dispatch, equal split (7 STC / 7 Main Gate buses)          |
| P2  | Zone-based dispatch, demand-matched split (6 STC / 8 Main Gate buses) |

## Model

- Arrivals: non-homogeneous Poisson process (Lewis–Shedler thinning), 14:00–17:00, peak at 15:15
- Travel times: log-normal noise, peak-traffic factor, random incidents
- Metrics: mean / 95th percentile / max wait, peak queue, wait per terminal, fleet utilisation
- 50 replications per configuration, 95% confidence intervals

## Files

| File               | Purpose                                                             |
| ------------------ | ------------------------------------------------------------------- |
| `muet_sim.py`      | Simulator (config, policies, verification checks)                   |
| `experiments.py`   | What-if studies (fleet size, demand, bus split, traffic) and charts |
| `make_diagrams.py` | State diagrams and flowchart                                        |
| `figures/`         | Generated charts and `results.json`                                 |

## How to run

```bash
pip install -r requirements.txt
python muet_sim.py        # verification checks + policy comparison
python experiments.py     # all what-if studies, writes figures/
python make_diagrams.py   # diagrams
```

All model parameters are in the `Config` class in `muet_sim.py`.

## Main results (assumed parameters)

| Policy      | Mean wait (min) | 95th pct (min) | Wait STC / Main Gate (min) |
| ----------- | --------------- | -------------- | -------------------------- |
| P0 Static   | 9.96            | 28.5           | 3.0 / 14.6                 |
| P1 Zone 7/7 | 4.42            | 12.8           | 2.6 / 5.6                  |
| P2 Zone 6/8 | 3.46            | 9.0            | 3.2 / 3.6                  |

## Limitations

No measured MUET data was available. All demand and travel parameters are assumptions, so absolute values are not
measurements of MUET; only the relative comparison between policies is meaningful. Replace the values in `Config`
with real counts and GPS data to calibrate the model.
