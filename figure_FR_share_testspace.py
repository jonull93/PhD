import pandas as pd
import pickle
import matplotlib.pyplot as plt
from os import path

# ---- input
# takes manual or pickled data and turns it into DataFrame
#           2020    2025    ..
# thermal   0.1     0.05
# VRE       0.6     0.8
# ..
#
# optionally give series for a line on secondary y axis

region = "brit"
mode = "lowFlex"
timestep = 6
# data = pickle.load(open(rf"C:\Users\jonull\git\python\PickleJar\data_results_{timestep}h.pickle", "rb"))
data = pickle.load(open(path.relpath(rf"PickleJar\data_results_{timestep}h.pickle"), "rb"))
years = [2020, 2025, 2030, 2040]
thermal = [0.45, 0.3, 0.2, 0.15]
VRE = [0.5, 0.1, 0.1, 0.05]
ESS = [0, 0.5, 0.6, 0.7]
BEV = [0.001, 0, 0, 0]
PtH = [0.001, 0, 0, 0]
hydro = [0.05, 0.1, 0.1, 0.1]

FR_price = [100, 60, 15, 5]
df = pd.DataFrame(data=
                  {"Thermals": thermal,
                   "VRE": VRE,
                   "ESS": ESS,
                   "BEV": BEV,
                   "PtH": PtH,
                   "Hydro": hydro
                   }, index=[2020, 2025, 2030, 2040]).round(decimals=4)
print(df)

# ---- plotting
# takes DataFrame and plots stacked area and optionally a line on secondary y axis
fig, axes = plt.subplots(ncols=3, nrows=1, figsize=(10, 5))
for i in range(3):
    ax = df.plot.bar(stacked=True, rot=13, ax=axes[i])
    ax.set_xticklabels(["2020", "Short-term", "Intermediate\n-term", "Long-term"])
    # ax.set_xticks(df.index)
    ax.set_title(f"Reserve share and cost, {region}, {mode}")
    ax.set_ylabel("Reserve share per technology")
    current_handles, current_labels = plt.gca().get_legend_handles_labels()
    ax2 = ax.twinx()
    ax2.set_ylabel("Total reserve cost each year")
    line = ax2.plot(FR_price, "k--")
    handles = current_handles + line
    labels = [h.get_label() for h in handles]
    labels[-1] = "Cost"
    ax.legend(handles, labels)
    ax2.set_ylim(ymin=0)
    if i>0: ax.get_legend().remove()
plt.show()
# plt.savefig(rf"figures\reserve_share_{region}_{mode}.png")
