import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

OUT = "figures"
def box(ax, x, y, w, h, text, fc="#e8f0fe", fs=7.5):
    ax.add_patch(FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec="#333", lw=1))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs)
def diamond(ax, x, y, w, h, text, fs=7):
    ax.add_patch(Polygon([(x, y+h/2), (x+w/2, y), (x, y-h/2), (x-w/2, y)], fc="#fff4d6", ec="#333", lw=1))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs)
def arrow(ax, p, q, text=None, off=(0, 0.12), rad=0.0):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="->", color="#333", lw=1, connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p[0]+q[0])/2 + off[0], (p[1]+q[1])/2 + off[1], text, fontsize=6.5, ha="center", color="#444")
def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off"); return fig, ax

# Bus state diagram
fig, ax = canvas(7, 2.9)
box(ax, 0.9, 2.0, 1.4, 0.6, "Holding at\nterminal")
box(ax, 2.7, 2.0, 1.4, 0.6, "Boarding\n(FCFS, ≤ C)")
box(ax, 4.5, 2.0, 1.4, 0.6, "Travel to\ncampus")
box(ax, 6.2, 2.0, 1.2, 0.6, "Unloading")
box(ax, 3.5, 0.7, 2.2, 0.6, "Return to own terminal")
arrow(ax, (1.6, 2.0), (2.0, 2.0), "full or\nwaited 4 min", off=(0, 0.35))
arrow(ax, (3.4, 2.0), (3.8, 2.0))
arrow(ax, (5.2, 2.0), (5.6, 2.0))
arrow(ax, (6.2, 1.7), (4.6, 0.8), rad=-0.15)
arrow(ax, (2.4, 0.7), (0.9, 1.7), rad=-0.2)
ax.text(3.5, 2.85, "Zone-based bus (P1, P2): each bus serves one terminal", ha="center", fontsize=8, weight="bold")
plt.savefig(f"{OUT}/diag_bus_states.png", dpi=200, bbox_inches="tight"); plt.close()

# Passenger state diagram
fig, ax = canvas(7.6, 2.0)
box(ax, 0.8, 0.8, 1.3, 0.6, "Arrives\n(Poisson)")
box(ax, 3.0, 0.8, 1.6, 0.6, "Waiting in\nterminal queue")
box(ax, 5.3, 0.8, 1.1, 0.6, "On bus")
box(ax, 7.0, 0.8, 1.3, 0.6, "Arrived\nat campus")
arrow(ax, (1.45, 0.8), (2.2, 0.8))
arrow(ax, (3.8, 0.8), (4.75, 0.8), "bus has a seat", off=(0, 0.22))
arrow(ax, (5.85, 0.8), (6.35, 0.8), "unload", off=(0, 0.22))
ax.annotate("", xy=(2.5, 1.12), xytext=(3.5, 1.12), arrowprops=dict(arrowstyle="->", lw=1, color="#333", connectionstyle="arc3,rad=1.6"))
ax.text(3.0, 2.05, "bus full: stay in queue", fontsize=6.5, ha="center", color="#444")
ax.set_ylim(0.3, 2.2)
plt.savefig(f"{OUT}/diag_passenger_states.png", dpi=200, bbox_inches="tight"); plt.close()

# Flowchart (compact)
fig, ax = canvas(3.4, 3.55)
X = 1.7
box(ax, X, 3.3, 2.7, 0.34, "Read config, seed RNG, create buses", fs=6.5)
box(ax, X, 2.8, 2.7, 0.34, "Generate arrivals (thinning) per terminal", fs=6.5)
diamond(ax, X, 2.15, 2.5, 0.66, "Bus ready to depart?\n(policy rule)", fs=6.5)
box(ax, X, 1.5, 2.7, 0.42, "Board FCFS (≤ capacity), travel to\ncampus, unload, return", fs=6.5)
diamond(ax, X, 0.85, 2.5, 0.62, "Arrivals over and\nqueues empty?", fs=6.5)
box(ax, X, 0.22, 2.7, 0.3, "Compute KPIs, export results", fs=6.5)
arrow(ax, (X, 3.13), (X, 2.97)); arrow(ax, (X, 2.63), (X, 2.48))
arrow(ax, (X, 1.82), (X, 1.71), "yes", off=(0.2, 0))
arrow(ax, (X, 1.29), (X, 1.16))
arrow(ax, (X, 0.54), (X, 0.37), "yes", off=(0.2, 0))
ax.plot([0.45, 0.12, 0.12, X], [2.15, 2.15, 2.5, 2.5], color="#333", lw=1)
ax.annotate("", xy=(X, 2.48), xytext=(X, 2.5), arrowprops=dict(arrowstyle="->", lw=1, color="#333"))
ax.text(0.2, 2.2, "no", fontsize=6, color="#444")
ax.plot([2.95, 3.3, 3.3], [0.85, 0.85, 2.15], color="#333", lw=1)
ax.annotate("", xy=(2.95, 2.15), xytext=(3.3, 2.15), arrowprops=dict(arrowstyle="->", lw=1, color="#333"))
ax.text(3.05, 0.92, "no", fontsize=6, color="#444")
ax.set_ylim(0.0, 3.55)
plt.savefig(f"{OUT}/diag_flowchart.png", dpi=250, bbox_inches="tight"); plt.close()
print("ok")
