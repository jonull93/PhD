import pickle
import pandas as pd
import matplotlib.pyplot as plt

data = pickle.load(open(r"C:\git\quality-of-life-scripts\PickleJar\data_results_3h.pickle", "rb"))
scen = "nordic_lowFlex_noFC_2020_3h"
cap = data[scen]["tot_cap"].loc[slice(None), "SE_S"]
cap.drop("HP", inplace=True)
var_cost = {"H_CHP": 30, "G": 75, "G_CHP": 65, "G_peak": 140, "W": 40, "W_CHP": 35, "WA_CHP": 5, "U": 5, "WG_peak": 200,
            "RO": 45}
for tech in cap.index:
    if "WO" in tech or "PV" in tech:
        var_cost[tech] = 1

var_cost_df = pd.DataFrame.from_dict(var_cost, orient="index", columns=["var_cost"])
cap = var_cost_df.join(pd.DataFrame(cap, columns=["cap"]))
cap.sort_values(by="var_cost", inplace=True)
cap["cumcap"] = cap["cap"].cumsum()
print(cap)
plt.plot(cap["cumcap"], cap["var_cost"])
plt.text(3.3, 5, "VRE")
plt.text(9, 8, "Nuclear")
plt.text(17, 45, "Thermals\n& Hydro", bbox=dict(facecolor='white', alpha=0.5, edgecolor="none", pad=2))
plt.xlabel("Power [GW]")
plt.ylabel("Price [€/MWh]")
plt.plot([11,16,16.2,22.4],[200, 170, 10, 5])
plt.text(9.3, 170, "High-price\naverse consumers")
plt.text(14.5, 100, "Regular\nconsumers", bbox=dict(facecolor='white', alpha=0.5, edgecolor="none", pad=2))
plt.text(17.5, 14, "Opportunistic\nconsumption")
plt.legend(["Supply", "Demand"])
plt.title("Example of supply-and-demand in electricity market")
plt.tight_layout()
plt.savefig("figures\\supply_and_demand.png",dpi=400,)
plt.show()