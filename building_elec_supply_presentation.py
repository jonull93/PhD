import pickle
import pandas as pd
import matplotlib.pyplot as plt
from my_utils import print_red, print_green, print_cyan
from order_cap import VRE

scen = "nordic_lowFlex_noFC_2040"
picklefile = "data_results_1h_lowFlex.pickle"

data = pickle.load(open(rf"PickleJar/{picklefile}", "rb"))
scendata = data[scen]

# Just the load
fig1, ax1 = plt.subplots()
load = scendata["demand"]
twload = load.sum(axis=0).iloc[24:168+24]
plt.plot(twload, label="Load")
ylim = ax1.get_ylim()
ax1.set_ylim([0,ylim[1]])
ax1.set_xticks(ticks=range(0, 8*24, 24), labels=range(1, 9))
ax1.set_xlabel("Day")
ax1.set_ylabel("Power [GWh/h]")
ax1.legend()
ax1.set_title("Load during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.savefig(r"figures/presentation_load.png", dpi=300)


# Overlayed with VRE prod
fig2, ax2 = plt.subplots()
load = scendata["demand"]
twload = load.sum(axis=0).iloc[24:168+24]
gen = scendata["gen"].sum(axis=0, level=0)
VRE = gen.reindex(index=VRE).dropna()
print(VRE)
"""
plt.plot(twload, label="Load")
ylim = ax1.get_ylim()
ax1.set_ylim([0,ylim[1]])
ax1.set_xticks(ticks=range(0, 8*24, 24), labels=range(1, 9))
ax1.set_xlabel("Day")
ax1.set_ylabel("Power [GWh/h]")
ax1.legend()
ax1.set_title("Load during a winter week in northern Europe, 2040")
plt.tight_layout()
plt.show()
plt.savefig(r"figures/presentation_load.png", dpi=300)
"""

# Net load


# Overlayed with hydro cap