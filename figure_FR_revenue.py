import sys
import os
import pickle
import order_cap
import pandas as pd
import matplotlib.pyplot as plt
from my_utils import color_dict, order_cap, add_in_dict, tech_names, scen_names, print_cyan, print_red, print_green, year_names

file_suffix = ""
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
timestep = 6
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))

total_rev = {}
FR_rev = {}
FR_share = {}
scenarios = []
fig, axs = plt.subplots(nrows=3, ncols=2, figsize=(6, 7))
for i_r, region in enumerate(["nordic", "brit", "iberia"]):
    for i_f, flex in enumerate(["lowFlex", "highFlex"]):
        for FC in ["fullFC"]:
            df = pd.DataFrame()
            for x, year in enumerate([2020, 2025, 2030, 2040]):
                # Gathering needed data
                scen = f"{region}_{flex}_{FC}_{year}_{timestep}h"
                scenarios.append(scen)
                print_cyan(scen)
                #scen = "nordic_lowFlex_fullFC_2025_6h"
                try:
                    total_rev[scen] = data[scen]["tech_revenue"]
                except KeyError: continue
                PtH = ["EB", "HP"]
                if "fullFC" in FC:
                    FR_rev[scen] = data[scen]["tech_revenue_FR"]
                    df[year] = FR_rev[scen]
                    FR_share[scen] = FR_rev[scen]/total_rev[scen]
        # Plotting the data
        print(df)
        df.T.plot.bar(ax=axs[i_r,i_f], stacked=True, legend=None)
plt.show()
                    #inertia_rev = data[scen]["tech_revenue_inertia"]
                    #FC_inertia = FR_rev+inertia_rev
                    #print_green((FR_rev[scen]/(total_rev[scen])).sort_values(ascending=False)[:10])
                #else:
                    #print_red(total_rev[scen].sort_values(ascending=False)[:10])

