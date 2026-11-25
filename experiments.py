"""What-if experiments and charts for muet_sim.py (Abdul Sami Shaikh, 148)."""
import json, math, os
from dataclasses import replace
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from muet_sim import Config, BusSystem, POLICIES, STC, MG

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
N = 50
COL = {"P0": "#d62728", "P1": "#2ca02c", "P2": "#1f77b4"}
LAB = {"P0": "P0 Static", "P1": "P1 Zone 7/7", "P2": "P2 Zone demand-fit"}


def policy(key, fleet):
    """Return (mode, split) for a fleet size. P2 gives Main Gate 60% of buses."""
    if key == "P0":
        return "static", None
    if key == "P1":
        return "zone", (fleet - fleet // 2, fleet // 2)
    mg = round(0.6 * fleet)
    return "zone", (fleet - mg, mg)


def stats(cfg, mode, split, n=N):
    rows = [BusSystem(cfg, mode, split, s).run() for s in range(n)]
    f = lambda k: float(np.mean([r[k] for r in rows]))
    ci = lambda k: float(1.96 * np.std([r[k] for r in rows], ddof=1) / math.sqrt(n))
    return {k: f(k) for k in ("mean", "p95", "max", "peak_q", "stc", "mg", "util", "load")} | \
           {"mean_ci": ci("mean"), "p95_ci": ci("p95")}


def collect(cfg, mode, split, n=N):
    waits, traces = [], []
    for s in range(n):
        b = BusSystem(cfg, mode, split, s); b.run()
        waits += b.waits[0] + b.waits[1]; traces.append(b.queue_trace)
    L = min(map(len, traces))
    return np.array(waits), np.mean([t[:L] for t in traces], axis=0)


R = {}
base = Config()

# 1. baseline comparison + per-policy collections
R["main"] = {}; waits = {}; traces = {}
for key in COL:
    mode, split = policy(key, base.fleet)
    R["main"][key] = stats(base, mode, split)
    waits[key], traces[key] = collect(base, mode, split)

# 2. fleet size
fleets = list(range(10, 17))
R["fleet"] = {k: [stats(replace(base, fleet=f), *policy(k, f)) for f in fleets] for k in COL}
# 3. demand
scales = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
R["demand"] = {k: [stats(replace(base, demand_scale=s), *policy(k, 14)) for s in scales] for k in COL}
# 4. MG bus count (zone split sweep, 14 buses)
mgs = list(range(4, 11))
R["split"] = [stats(base, "zone", (14 - m, m)) for m in mgs]
# 5. traffic uncertainty
traffic = [(0.10, 0.01), (0.20, 0.03), (0.30, 0.06), (0.40, 0.10)]
R["traffic"] = {k: [stats(replace(base, noise=s, incident_p=p), *policy(k, 14)) for s, p in traffic] for k in COL}

json.dump(R, open(os.path.join(OUT, "results.json"), "w"), indent=1)

# ---------------- charts (sized for one column of a two-column paper) ----------------
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "legend.fontsize": 6,
                     "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "axes.grid": True, "grid.alpha": .3})
CW = 3.4
def save(name): plt.tight_layout(pad=0.4); plt.savefig(f"{OUT}/{name}.png", dpi=250); plt.close()

# Fig 4: demand vs zone capacity (analytic bottleneck), both terminals in one axis
t = np.linspace(0, base.window, 400)
def zone_cap(k, n, tt):
    c = base
    Tc = 2 * c.leg_out[k] * c.kappa(tt) + c.unload + c.dwell + c.capacity * c.board_per_pax
    return n * c.capacity / Tc
plt.figure(figsize=(CW, 2.1))
for k, n, col in ((STC, 6, "#4c72b0"), (MG, 8, "#dd8452")):
    lam = np.array([base.rate(x, k) for x in t]); cap = np.array([zone_cap(k, n, x) for x in t])
    plt.plot(t, lam, color=col, label=f"{['STC','Main Gate'][k]} arrivals λ(t)")
    plt.plot(t, cap, "--", color=col, label=f"{['STC','Main Gate'][k]} capacity μ(t), {n} buses")
    plt.fill_between(t, lam, cap, where=lam > cap, color="#d62728", alpha=.25)
plt.xlabel("Minutes since 14:00"); plt.ylabel("Passengers / min"); plt.legend(loc="upper left", ncol=1)
plt.ylim(0, 17.5); save("fig1_bottleneck")

# Fig 5: queue over time
plt.figure(figsize=(CW, 1.8))
for k in COL: plt.plot(traces[k], label=LAB[k], color=COL[k], lw=1.1)
plt.axvspan(55, 100, color="grey", alpha=.12, label="Peak traffic")
plt.xlabel("Minutes since 14:00"); plt.ylabel("Students waiting"); plt.legend(); save("fig2_queue_over_time")

# Fig 6: bars mean / p95 / peak queue
fig, ax = plt.subplots(1, 3, figsize=(CW, 1.7))
for a, (m, ttl) in zip(ax, (("mean", "Mean wait (min)"), ("p95", "95th pct wait (min)"), ("peak_q", "Peak queue"))):
    vals = [R["main"][k][m] for k in COL]; errs = [R["main"][k].get(m + "_ci", 0) for k in COL]
    a.bar(list(COL), vals, yerr=errs, color=list(COL.values()), capsize=2); a.set_title(ttl)
save("fig3_policy_bars")

# Fig 7: per-terminal wait
plt.figure(figsize=(CW, 1.6)); x = np.arange(3)
plt.bar(x - .2, [R["main"][k]["stc"] for k in COL], .4, label="STC", color="#4c72b0")
plt.bar(x + .2, [R["main"][k]["mg"] for k in COL], .4, label="Main Gate", color="#dd8452")
plt.xticks(x, [LAB[k] for k in COL]); plt.ylabel("Mean wait (min)"); plt.legend(); save("fig4a_terminal_wait")

# Fig 8: CDF
plt.figure(figsize=(CW, 1.6))
for k in COL:
    w = np.sort(waits[k]); plt.plot(w, np.arange(1, len(w) + 1) / len(w), label=LAB[k], color=COL[k], lw=1.1)
plt.xlabel("Wait (min)"); plt.ylabel("CDF"); plt.legend(loc="lower right"); save("fig4b_cdf")

# Fig 9: fleet size (mean on top, 95th pct below)
fig, ax = plt.subplots(2, 1, figsize=(CW, 2.3), sharex=True)
for k in COL:
    ax[0].plot(fleets, [r["mean"] for r in R["fleet"][k]], "o-", ms=3, label=LAB[k], color=COL[k], lw=1)
    ax[1].plot(fleets, [r["p95"] for r in R["fleet"][k]], "o-", ms=3, label=LAB[k], color=COL[k], lw=1)
ax[0].set_ylabel("Mean wait (min)"); ax[1].set_ylabel("95th pct wait (min)"); ax[1].set_xlabel("Fleet size (buses)")
ax[0].legend(); save("fig5_fleet_size")

# Fig 10: demand
plt.figure(figsize=(CW, 1.95))
for k in COL: plt.plot([s * 100 for s in scales], [r["mean"] for r in R["demand"][k]], "o-", ms=3, label=LAB[k], color=COL[k], lw=1)
plt.xlabel("Demand (% of baseline)"); plt.ylabel("Mean wait (min)"); plt.legend(); save("fig6_demand")

# Fig 11: split sweep
plt.figure(figsize=(CW, 1.95))
plt.plot(mgs, [r["mean"] for r in R["split"]], "o-", ms=3, label="Mean", color="#1f77b4", lw=1)
plt.plot(mgs, [r["p95"] for r in R["split"]], "s-", ms=3, label="95th pct", color="#d62728", lw=1)
plt.xlabel("Buses assigned to Main Gate (of 14)"); plt.ylabel("Wait (min)"); plt.legend(); save("fig7_split_sweep")

# Fig 12: traffic
plt.figure(figsize=(CW, 1.95))
for k in COL: plt.plot(range(4), [r["mean"] for r in R["traffic"][k]], "o-", ms=3, label=LAB[k], color=COL[k], lw=1)
plt.xticks(range(4), [f"σ={s}, {int(p*100)}% inc." for s, p in traffic], fontsize=6)
plt.ylabel("Mean wait (min)"); plt.legend(); save("fig8_traffic")

print("done")
for k in COL: print(k, {m: round(v, 2) for m, v in R["main"][k].items()})
print("fleet mean", {k: [round(r["mean"], 1) for r in R["fleet"][k]] for k in COL})
print("fleet p95", {k: [round(r["p95"], 1) for r in R["fleet"][k]] for k in COL})
print("demand mean", {k: [round(r["mean"], 1) for r in R["demand"][k]] for k in COL})
print("demand p95", {k: [round(r["p95"], 1) for r in R["demand"][k]] for k in COL})
print("split mean", [round(r["mean"], 1) for r in R["split"]], "p95", [round(r["p95"], 1) for r in R["split"]])
print("traffic mean", {k: [round(r["mean"], 1) for r in R["traffic"][k]] for k in COL})
