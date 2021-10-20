import pandas as pd
import pickle
import matplotlib.pyplot as plt

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
timestep = 12
data = pickle.load(open(rf"C:\Users\jonull\git\python\PickleJar\data_results_{timestep}h.pickle", "rb"))
years = [2020, 2025, 2030, 2040]
scenarios = [f"{region}_{mode}_fullFC_{y}_{timestep}h" for y in years]
thermal = [data[scen]["OR_value_share_thermal"] for scen in scenarios]  # [0.45, 0.3, 0.2, 0.15]
print(thermal)
VRE = [data[scen]["OR_value_share_VRE"] for scen in scenarios]  # [0.5, 0.1, 0.1, 0.05]
ESS = [data[scen]["OR_value_share_ESS"] for scen in scenarios]  # [0, 0.5, 0.6, 0.7]
BEV = [data[scen]["OR_value_share_BEV"] for scen in scenarios]  # [0.001, 0, 0, 0]
PtH = [data[scen]["OR_value_share_PtH"] for scen in scenarios]
hydro = [data[scen]["OR_value_share_hydro"] for scen in scenarios]  # [0.05, 0.1, 0.1, 0.1]

FR_price = [0, 0, 0, 0]
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
ax = df.plot(kind="area", linewidth=0)
ax.set_xticks(df.index)
ax.set_title(f"Reserve share and cost, {region}, {mode}")
ax.set_ylabel("Reserve share per technology")
ax2 = ax.twinx()
ax2.set_ylabel("Total reserve cost each year")
ax2.plot(df.index, FR_price, "k--")
ax2.set_ylim(ymin=0)
#plt.show()
plt.savefig(rf"figures\reserve_share_{region}_{mode}.png")
