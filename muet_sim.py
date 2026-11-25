"""
MUET Point (bus) system - discrete event simulation with SimPy.
Scenario: evening return window 14:00-17:00, peak around 15:15.
Compares a static timetable against zone-based (dedicated-terminal) dispatch.
Author: Abdul Sami Shaikh (148)   |   All parameters are ASSUMED values (see Config).
"""
import math
from collections import deque
from dataclasses import dataclass
import numpy as np
import simpy

STC, MG = 0, 1
NAMES = ("STC", "Main Gate")


@dataclass
class Config:
    window: float = 180.0            # minutes simulated (14:00-17:00)
    fleet: int = 14
    capacity: int = 45
    base_rate: float = 3.0           # pax/min, all day level
    peak_rate: float = 13.0          # extra pax/min at the peak centre
    peak_centre: float = 75.0        # minutes after 14:00 -> 15:15
    peak_width: float = 25.0
    share: tuple = (0.40, 0.60)      # demand split STC / Main Gate
    leg_out: tuple = (12.0, 15.0)    # terminal -> campus travel time (min)
    leg_link: float = 5.0            # STC -> Main Gate (static route only)
    unload: float = 2.0
    dwell: float = 0.5               # door time per stop
    board_per_pax: float = 2.1 / 60  # minutes per boarding passenger
    noise: float = 0.15              # log-normal sigma of travel time
    congestion: float = 1.25         # travel multiplier in peak traffic
    traffic_peak: tuple = (55.0, 100.0)
    incident_p: float = 0.03
    incident_delay: float = 8.0
    headway: float = 4.0             # static timetable headway (min)
    hold_max: float = 4.0            # zone policy: max time a bus holds
    tick: float = 0.25
    demand_scale: float = 1.0

    def rate(self, t, k):
        s = self.peak_width
        lam = self.base_rate + self.peak_rate * math.exp(-(t - self.peak_centre) ** 2 / (2 * s * s))
        return self.demand_scale * self.share[k] * lam

    def kappa(self, t):
        return self.congestion if self.traffic_peak[0] <= t <= self.traffic_peak[1] else 1.0

    def expected_arrivals(self):
        s, tp, W = self.peak_width, self.peak_centre, self.window
        phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
        gauss = self.peak_rate * s * math.sqrt(2 * math.pi) * (phi((W - tp) / s) - phi(-tp / s))
        return self.demand_scale * (self.base_rate * W + gauss)


class BusSystem:
    def __init__(self, cfg, mode, split=None, seed=0):
        self.c, self.mode, self.split = cfg, mode, split
        self.rng = np.random.default_rng(seed)
        self.env = simpy.Environment()
        self.q = [deque(), deque()]               # arrival times per terminal
        self.waits = [[], []]
        self.loads, self.queue_trace = [], []
        self.busy, self.arrived = 0.0, 0
        self.depot = list(range(cfg.fleet))       # idle buses (static mode)
        self.next_slot = 0.0

    # ---------- passengers ----------
    def arrivals(self, k):
        c = self.c
        lam_max = c.demand_scale * c.share[k] * (c.base_rate + c.peak_rate)
        t = 0.0
        while True:                                # Lewis-Shedler thinning
            t += self.rng.exponential(1.0 / lam_max)
            if t > c.window:
                return
            yield self.env.timeout(t - self.env.now)
            if self.rng.random() <= c.rate(t, k) / lam_max:
                self.q[k].append(self.env.now)
                self.arrived += 1

    def sampler(self):
        while True:
            self.queue_trace.append(len(self.q[0]) + len(self.q[1]))
            yield self.env.timeout(1.0)

    # ---------- bus helpers ----------
    def travel(self, base):
        c = self.c
        d = base * c.kappa(self.env.now) * self.rng.lognormal(-0.5 * c.noise ** 2, c.noise)
        if self.rng.random() < c.incident_p:
            d += c.incident_delay
        self.busy += d
        return d

    def board(self, k, free):
        n = 0
        while self.q[k] and n < free:
            self.waits[k].append(self.env.now - self.q[k].popleft())
            n += 1
        d = self.c.dwell + n * self.c.board_per_pax
        self.busy += d
        return n, d

    # ---------- P0: static timetable (bus visits STC then Main Gate) ----------
    def static_dispatcher(self):
        while True:
            if self.env.now >= self.next_slot and self.depot:
                self.next_slot += self.c.headway
                self.env.process(self.static_bus(self.depot.pop(0)))
            yield self.env.timeout(self.c.tick)

    def static_bus(self, bus):
        c = self.c
        yield self.env.timeout(self.travel(c.leg_out[STC]))
        n1, d = self.board(STC, c.capacity)
        yield self.env.timeout(d)
        yield self.env.timeout(self.travel(c.leg_link))
        n2, d = self.board(MG, c.capacity - n1)
        yield self.env.timeout(d)
        yield self.env.timeout(self.travel(c.leg_out[MG]))
        yield self.env.timeout(c.unload)
        self.busy += c.unload
        self.loads.append(n1 + n2)
        self.depot.append(bus)

    # ---------- P1/P2: zone-based, bus dedicated to one terminal ----------
    def zone_bus(self, k):
        c = self.c
        while True:
            while True:                            # hold until full or oldest waited too long
                q = self.q[k]
                if len(q) >= c.capacity or (q and self.env.now - q[0] >= c.hold_max):
                    break
                yield self.env.timeout(c.tick)
            n, d = self.board(k, c.capacity)
            yield self.env.timeout(d)
            yield self.env.timeout(self.travel(c.leg_out[k]))
            yield self.env.timeout(c.unload)
            self.busy += c.unload
            self.loads.append(n)
            yield self.env.timeout(self.travel(c.leg_out[k]))   # return to own terminal

    # ---------- run ----------
    def run(self):
        for k in (STC, MG):
            self.env.process(self.arrivals(k))
        self.env.process(self.sampler())
        if self.mode == "static":
            self.env.process(self.static_dispatcher())
        else:
            for k, n_buses in enumerate(self.split):
                for _ in range(n_buses):
                    self.env.process(self.zone_bus(k))
        horizon = self.c.window + 150
        self.env.run(until=horizon)
        allw = np.array(self.waits[0] + self.waits[1])
        fleet = self.c.fleet
        return dict(
            mean=allw.mean(), p95=np.percentile(allw, 95), max=allw.max(),
            peak_q=max(self.queue_trace),
            stc=np.mean(self.waits[0]), mg=np.mean(self.waits[1]),
            load=np.mean(self.loads) / self.c.capacity,
            util=self.busy / (fleet * horizon),
            unserved=len(self.q[0]) + len(self.q[1]),
            max_load=max(self.loads), arrived=self.arrived,
        )


POLICIES = {
    "P0 Static timetable":      ("static", None),
    "P1 Zone 7/7 (equal)":      ("zone", (7, 7)),
    "P2 Zone 6/8 (demand-fit)": ("zone", (6, 8)),
}


def replicate(cfg, mode, split, n=50, seed0=0):
    rows = [BusSystem(cfg, mode, split, seed0 + i).run() for i in range(n)]
    out = {}
    for key in rows[0]:
        v = np.array([r[key] for r in rows], dtype=float)
        out[key] = (v.mean(), 1.96 * v.std(ddof=1) / math.sqrt(n))
    return out, rows


def compare(cfg=None, n=50):
    cfg = cfg or Config()
    print(f"{'Policy':26s}{'Mean':>14s}{'P95':>14s}{'Max':>8s}{'PeakQ':>8s}{'STC':>7s}{'MG':>7s}{'Util':>7s}")
    results = {}
    for name, (mode, split) in POLICIES.items():
        r, _ = replicate(cfg, mode, split, n)
        results[name] = r
        print(f"{name:26s}{r['mean'][0]:8.2f}±{r['mean'][1]:4.2f}{r['p95'][0]:8.1f}±{r['p95'][1]:4.1f}"
              f"{r['max'][0]:8.1f}{r['peak_q'][0]:8.0f}{r['stc'][0]:7.1f}{r['mg'][0]:7.1f}{r['util'][0]:7.2f}")
    return results


def verify(cfg=None):
    cfg = cfg or Config()
    ok = True
    for name, (mode, split) in POLICIES.items():
        _, rows = replicate(cfg, mode, split, n=20, seed0=500)
        served_all = all(r["unserved"] == 0 for r in rows)
        cap_ok = all(r["max_load"] <= cfg.capacity for r in rows)
        print(f"{name:26s} all served: {served_all} | load <= capacity: {cap_ok}")
        ok &= served_all and cap_ok
    sim = np.mean([r["arrived"] for r in rows])
    print(f"arrivals: simulated {sim:.1f} vs analytic {cfg.expected_arrivals():.1f}")
    return ok


if __name__ == "__main__":
    print("--- verification ---"); verify()
    print("--- comparison (50 replications) ---"); compare()
