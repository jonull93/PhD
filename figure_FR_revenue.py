import sys
import os
import pickle
import order_cap
import pandas as pd
import matplotlib.pyplot as plt
from my_utils import year_names_twolines, color_dict, order_cap, add_in_dict, tech_names, scen_names, print_cyan, print_red, print_green, year_names, order_map_cap
from order_cap import baseload, midload, peak, wind, PV, PtH, CHP, thermals, order_cap
from matplotlib.lines import Line2D

file_suffix = ""
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
timestep = 6
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))
print([i for i in data.keys() if "nordic" in i and "highFlex" in i])


def aggregate_in_df(df, index_list: list, new_index: str):
    temp = df.loc[df.index.intersection(index_list)].sum()
    df.drop(index_list, inplace=True, errors='ignore')
    df.loc[new_index] = temp
    return df


thermals = [i for i in thermals if i not in CHP]
total_rev = {}
FR_rev = {}
FR_share = {}
scenarios = []
techs = []
fig, axs = plt.subplots(nrows=4, ncols=3, figsize=(7, 8))
for i_y, year in enumerate([2020, 2025, 2030, 2040]):
    for i_r, region in enumerate(["nordic", "brit", "iberia"]):
        df_rev = pd.DataFrame()
        df_share = pd.DataFrame()
        for i_f, flex in enumerate(["lowFlex", "highFlex"]):
            for FC in ["fullFC"]:
                # Gathering needed data
                scen = f"{region}_{flex}_{FC}_{year}_{timestep}h"
                scenarios.append(scen)
                print_cyan(scen)
                #scen = "nordic_lowFlex_fullFC_2025_6h"
                try:
                    total_rev[scen] = data[scen]["tech_revenue"].sum(level=0)
                except KeyError: continue
                except AttributeError as e:
                    continue
                if "fullFC" in FC:
                    """FR_rev[scen].loc["Base"] = FR_rev[scen].loc[FR_rev[scen].index.intersection(baseload)].sum()
                    FR_rev[scen].drop(baseload, inplace=True, errors='ignore')
                    FR_rev[scen].loc["Peak"] = FR_rev[scen].loc[FR_rev[scen].index.intersection(peak)].sum()
                    FR_rev[scen].drop(peak, inplace=True, errors='ignore')
                    FR_rev[scen].loc["CHP"] = FR_rev[scen].loc[FR_rev[scen].index.intersection(CHP)].sum()
                    FR_rev[scen].drop(CHP, inplace=True, errors='ignore')"""
                    FR_rev[scen] = data[scen]["tech_revenue_FR"].sum(level=0)
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], wind, "Wind")
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], PV, "Solar PV")
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], thermals, "Thermals")
                    FR_rev[scen].drop(CHP, inplace=True, errors='ignore')
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], ["RO","RR"], "Hydro")
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], PtH, "PtH")
                    df_rev[flex] = (FR_rev[scen] / 1000).round(1)
                    df_rev["sort_by"] = df_rev.index.get_level_values(0).map(order_map_cap)
                    df_rev.sort_values("sort_by", inplace=True)
                    df_rev.drop(columns="sort_by", inplace=True)
                    for i in df_rev.index:
                        if i not in techs:
                            techs.append(i)
                    print(techs)
                    total_rev[scen] = aggregate_in_df(total_rev[scen], wind, "Wind")
                    total_rev[scen] = aggregate_in_df(total_rev[scen], PV, "Solar PV")
                    total_rev[scen] = aggregate_in_df(total_rev[scen], thermals, "Thermals")
                    total_rev[scen].drop(CHP, inplace=True, errors='ignore')
                    total_rev[scen] = aggregate_in_df(total_rev[scen], ["RO","RR"], "Hydro")
                    total_rev[scen] = aggregate_in_df(total_rev[scen], PtH, "PtH")
                    total_rev[scen].drop("W_HOB", inplace=True, errors='ignore')
                    # print_red(FR_rev[scen])
                    # print_cyan(total_rev[scen])
                    df_share[flex] = (FR_rev[scen]/total_rev[scen]).round(4)
                    print_green(df_share[flex])
        # Plotting the data
        df_rev.T.plot.bar(ax=axs[i_y, i_r], stacked=True, legend=None, color=[color_dict[tech] for tech in df_rev.index], zorder=-1)
        axs[i_y, i_r].set_xticklabels(df_rev.T.index, rotation=20, ha="center", va="top", rotation_mode='anchor')
        ax2 = axs[i_y, i_r].twinx()
        ax2.scatter(x=[0 for i in range(len(df_share))], y=df_share["lowFlex"], marker='d', edgecolors='black', linewidths=0.5,
                    c=[color_dict[tech] for tech in df_share.index], zorder=1)
        if "highFlex" in df_share.keys():
            ax2.scatter(x=[1 for i in range(len(df_share))], y=df_share["highFlex"], marker='d', edgecolors='black', linewidths=0.5,
                        c=[color_dict[tech] for tech in df_share.index], zorder=1)
        ax2.set_ylim([0, 1])
        ax2.set_yticks([i/5 for i in range(6)])
        #df_share.T.plot.scatter(ax=axs[i_y, i_r], c=[color_dict[tech] for tech in df_rev.index],)
        if year == 2020: axs[i_y,i_r].set_title(region.capitalize(), fontsize=13)
        if i_r == 0:
            axs[i_y,i_r].text(-1, 0.5, year_names_twolines[year].capitalize(), transform=axs[i_y, i_r].transAxes,
                                       ha="center", va="center", fontsize=12)
        if year != 2040: axs[i_y,i_r].xaxis.set_ticklabels([])

for i, tech in enumerate(techs):
    if tech in tech_names.keys():
        techs[i] = tech_names[tech]
sorted_techs = []
for tech in order_cap:
    if tech in techs:
        sorted_techs.append(tech)

plt.figtext(0.21, 0.5, "Revenue from reserves [M€/yr]", ha="center", va="center", rotation=90)
plt.figtext(1.02, 0.5, "Reserve share of total revenue [-]", ha="right", va="center", rotation=90)
lines = [Line2D([0], [0], color=color_dict[tech], lw=6) for tech in sorted_techs]
plt.tight_layout()
legend = fig.legend(lines, sorted_techs, loc="lower center", bbox_transform=axs[0, 1].transAxes, bbox_to_anchor=(0.5, 1.17), ncol=3)
fig_path = f"figures\\"
plt.savefig(fig_path+f"FR_revenue_{timestep}h.png", dpi=400, bbox_inches="tight")
plt.show()
                    #inertia_rev = data[scen]["tech_revenue_inertia"]
                    #FC_inertia = FR_rev+inertia_rev
                    #print_green((FR_rev[scen]/(total_rev[scen])).sort_values(ascending=False)[:10])
                #else:
                    #print_red(total_rev[scen].sort_values(ascending=False)[:10])

