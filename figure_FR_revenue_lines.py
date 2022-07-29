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
fig, axs = plt.subplots(nrows=3, ncols=1, figsize=(6, 7))
years = ["2020", "2025", "2030", "2040"]
regions = ["nordic", "brit", "iberia"]
flexes = ["lowFlex", "highFlex"]
df_rev = {tech: pd.DataFrame(0,pd.MultiIndex.from_product([regions,flexes],names=["Region","Flex"]), years)
                  for tech in ["bat", "PtH", "Thermals"]}
for i_y, year in enumerate(years):
    for i_r, region in enumerate(regions):
        df_share = pd.DataFrame()
        for i_f, flex in enumerate(flexes):
            FR_rev[region] = {flex: {}}
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
                    FR_rev[scen].drop(CHP, inplace=True, errors='ignore')  # CHP is part of thermals already
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], ["RO","RR"], "Hydro")
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], PtH, "PtH")
                    print(FR_rev[scen])
                    for tech in df_rev:
                        try: df_rev[tech].loc[(region,flex),year] = (FR_rev[scen][tech] / 1000).round(1)
                        except KeyError: continue
                    # df_rev["sort_by"] = df_rev.index.get_level_values(0).map(order_map_cap)
                    # df_rev.sort_values("sort_by", inplace=True)
                    # df_rev.drop(columns="sort_by", inplace=True)
                    for i in FR_rev[scen].index:
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
for i_t, tech in enumerate(["bat","PtH","Thermals"]):
    print_cyan(tech)
    print(df_rev[tech].T)
    df_rev[tech].T.plot(ax=axs[i_t], legend=None, color=['teal', 'teal', 'purple', 'purple', 'orange', 'orange'], marker='o', zorder=-1) #, color=color_dict["Battery"]
    for i_r, region in enumerate(regions):
        axs[i_t].fill_between(years,df_rev[tech].loc[(region,"lowFlex")],df_rev[tech].loc[(region,"highFlex")], alpha=0.3, color=['teal', 'purple','orange'][i_r])
    axs[i_t].set_title(tech.title(), fontsize=13)
    axs[i_t].set_xticks([0,1,2,3])
    axs[i_t].set_xticklabels([year_names[int(year)].capitalize() for year in years]) #, rotation=20, ha="center", va="top", rotation_mode='anchor'
if i_r == 0:
    axs[i_r].text(0.1, 0.5, year_names_twolines[year].capitalize(), transform=axs[i_r].transAxes,
                               ha="center", va="center", fontsize=12)
# if year != 2040: axs[i_y,i_r].xaxis.set_ticklabels([])

for i, tech in enumerate(techs):
    if tech in tech_names.keys():
        techs[i] = tech_names[tech]
sorted_techs = []
for tech in order_cap:
    if tech in techs:
        sorted_techs.append(tech)

#plt.figtext(0.21, 0.5, "Revenue from reserves [M€/yr]", ha="center", va="center", rotation=90)
#plt.figtext(1.02, 0.5, "Reserve share of total revenue [-]", ha="right", va="center", rotation=90)
lines = [Line2D([0], [0], color=color_dict[tech], lw=6) for tech in sorted_techs]
plt.tight_layout()
legend = fig.legend(lines, sorted_techs, loc="lower center", bbox_transform=axs[0].transAxes, bbox_to_anchor=(0.5, 1.17), ncol=3)
fig_path = f"figures\\"
plt.savefig(fig_path+f"FR_revenue_lines_{timestep}h.png", dpi=400, bbox_inches="tight")
plt.show()
                    #inertia_rev = data[scen]["tech_revenue_inertia"]
                    #FC_inertia = FR_rev+inertia_rev
                    #print_green((FR_rev[scen]/(total_rev[scen])).sort_values(ascending=False)[:10])
                #else:
                    #print_red(total_rev[scen].sort_values(ascending=False)[:10])

