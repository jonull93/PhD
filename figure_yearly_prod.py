import pickle
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
from my_utils import TECH, color_dict, order_map_cap, tech_names, scen_names, print_red, print_cyan, print_green

WON = ["WON"+a+str(b) for a in ["A","B"] for b in range(1, 6)]
wind = WON+["WOFF"]
PV = ["PVPA1", "PVPB1", "PVR1"]
hydro = ["RO","RR"]
fossil_thermal = ["b", "B_CHP", "H", "H_CHP", "G", "G_CHP", "WA_CHP", "G_peak"]
bio_thermal = ["W", "W_CHP", "WG_peak", "WG"]

def sum_in_df(df,to_sum,summed_name):
    rows = [i for i in df.index if i in to_sum]
    summed_rows = df.loc[rows].sum(axis=0).rename(summed_name)
    df.drop(rows, inplace=True)
    df = df.append(summed_rows)
    return df

def make_df_from_year(scen,data,year):
    df = pd.DataFrame(data[scen]["gen_per_eltech"], columns=[year])
    for name, to_sum in {"Wind":wind, "Solar PV":PV, "Fossil thermals":fossil_thermal, "Bio thermals":bio_thermal, "Hydro":hydro}.items():
        df = sum_in_df(df,to_sum,name)
    df.rename(index={"U": "Nuclear"}, inplace=True)
    return df.iloc[::-1]


def make_figure(data, region, mode, timestep, suffix="", years=None, ax=None, optional_title=False):
    plt.sca(ax)
    if years is None:
        years = [2020, 2025, 2030, 2040]
    dfs = {y: 0. for y in years}
    for year in years:
        scenario = f"{region}_{mode}_{year}{suffix}_{timestep}h"
        if timestep==1:
            scenario = f"{region}_{mode}_{year}{suffix}"
        dfs[year] = make_df_from_year(scenario,data,year)/1000
    # some ancillary code
    stripped_scenario = scenario.replace("_noFC", "").replace(f"_{year}", "")
    print_cyan("Starting", stripped_scenario)
    # starting the df manipulation
    df = pd.concat(dfs.values(), axis=1)
    df["sort_by"] = df.index.get_level_values(0).map(order_map_cap)
    df.sort_values("sort_by", inplace=True)
    df.drop(columns="sort_by", inplace=True)
    df.columns = range(len(df.columns))
    # plotting
    if ax is None:
        df.T.plot(kind="area", color=[color_dict[tech] for tech in df.index])
    else:
        df.T.plot(kind="area", ax=ax, color=[color_dict[tech] for tech in df.index])
    plt.xticks(range(len(df.columns)), ["Ref.\n2020", "Near-\nterm", "Mid-\nterm", "Long-\nterm"])
    if optional_title:
        plt.title(f"{regions_corrected[region]}, {optional_title}")
    else:
        plt.title(f"{region.capitalize()}, {mode[0].upper() + mode[1:]}") #"$\it{"+region.capitalize()+"}$"+f"
    return ax,df

timestep = 3
fig_path = f"figures\\"
os.makedirs(fig_path, exist_ok=True)
regions = ["nordic", "brit", "iberia"]
regions_corrected = {"brit": "Brit", "nordic": "Nordic+", "iberia": "Iberia"}
modes = ["lowFlex_noFC","highFlex_noFC"]
optional_titles = ["LowFlex", "HighFlex"]
file_suffix = ""
if len(file_suffix) > 0 and file_suffix[0] != "_": file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0 and scen_suffix[0] != "_": scen_suffix = "_" + scen_suffix

data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))
#data2 = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h_highFlex.pickle"), "rb"))
#for scen in data2:
#    print(scen)
#    if scen not in data:
#        data[scen] = data2[scen]
fig, axes = plt.subplots(nrows=len(modes), ncols=len(regions), figsize=(6+len(regions), 4+len(modes)))
for i_r, reg in enumerate(regions):
    for i_m, mode in enumerate(modes):
        ax, df = make_figure(data, reg, mode, timestep, suffix=scen_suffix, ax=axes[i_m,i_r], optional_title=optional_titles[i_m]) #ax=axes[i_m, i_r]
        if i_r+i_m > 0:
            if len(modes)==1:
                h, l = axes[0].get_legend_handles_labels()
            else:
                h,l = axes[0][0].get_legend_handles_labels()
        ax.get_legend().remove()

fig.legend(h, l, bbox_to_anchor=(0.5, -0.04), loc="lower center", ncol=6)
fig.suptitle("Generation per technology type", y=0.97, fontsize=14)
try:
    fig.supxlabel("Time-point", y=0.041)
    fig.supylabel("Electricity production [TWh/yr]")
except AttributeError:
    axes[0].set_ylabel("Electricity production [TWh/yr]")
    axes[1].set_xlabel("Time-point")
fig.tight_layout()
plt.savefig(fig_path+f"yearly_elec_prod_{timestep}h.png", dpi=300, bbox_inches="tight")
plt.savefig(fig_path+f"yearly_elec_prod_{timestep}h.svg", bbox_inches="tight")
plt.savefig(fig_path+f"yearly_elec_prod_{timestep}h.pdf", bbox_inches="tight")

