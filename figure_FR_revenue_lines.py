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
timestep = 3
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))


def aggregate_in_df(df, index_list: list, new_index: str):
    temp = df.loc[df.index.intersection(index_list)].sum()
    df.drop(index_list, inplace=True, errors='ignore')
    df.loc[new_index] = temp
    return df


thermals = [i for i in thermals if i not in CHP]
total_rev = {}
cap = {}
FR_rev = {}
FR_share = {}
scenarios = []
techs = []
years = ["2020", "2025", "2030", "2040"]
regions = ["nordic", "brit", "iberia"]
flexes = ["lowFlex", "highFlex"]
technologies_to_show = ["bat","PtH","thermals","Hydro"]
per_cap = False
fig, axs = plt.subplots(nrows=len(technologies_to_show), ncols=1, figsize=(7, 6))
df_rev = {tech: pd.DataFrame(0,pd.MultiIndex.from_product([regions,flexes],names=["Region","Flex"]), years)
                  for tech in technologies_to_show}
df_share = {flex: pd.DataFrame(0,pd.MultiIndex.from_product([regions,years],names=["Region","Year"]), technologies_to_show)
                  for flex in flexes}
for i_y, year in enumerate(years):
    for i_r, region in enumerate(regions):
        for i_f, flex in enumerate(flexes):
            FR_rev[region] = {flex: {}}
            for FC in ["fullFC"]:
                # Gathering needed data
                scen = f"{region}_{flex}_{FC}_{year}_{timestep}h"
                scenarios.append(scen)
                #print_cyan(scen)
                #scen = "nordic_lowFlex_fullFC_2025_6h"
                try:
                    total_rev[scen] = data[scen]["tech_revenue"].sum(level=0)
                    cap[scen] = data[scen]["tot_cap"].sum(level=0)
                except KeyError as e:
                    print(e)
                    continue
                except AttributeError as e:
                    print(e)
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
                    cap[scen] = aggregate_in_df(cap[scen], wind, "Wind")
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], PV, "Solar PV")
                    cap[scen] = aggregate_in_df(cap[scen], PV, "Solar PV")
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], thermals, "thermals")
                    cap[scen] = aggregate_in_df(cap[scen], thermals, "thermals")
                    FR_rev[scen].drop(CHP, inplace=True, errors='ignore')  # CHP is part of thermals already
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], ["RO","RR"], "Hydro")
                    cap[scen] = aggregate_in_df(cap[scen], ["RO", "RR"], "Hydro")
                    FR_rev[scen] = aggregate_in_df(FR_rev[scen], PtH, "PtH")
                    cap[scen] = aggregate_in_df(cap[scen], PtH, "PtH")
                    print(FR_rev[scen])
                    for tech in df_rev:
                        try:
                            if per_cap:
                                df_rev[tech].loc[(region,flex),year] = (FR_rev[scen][tech] / cap[scen][tech] / 1000).round(1)
                                if df_rev[tech].loc[(region,flex),year] > 10:
                                    print(tech)
                                    print((FR_rev[scen][tech] / 1000).round(1))
                                    print(cap[scen][tech])
                                    print(df_rev[tech].loc[(region,flex),year])
                            else:
                                df_rev[tech].loc[(region, flex), year] = (FR_rev[scen][tech] / 1000).round(1)
                        except KeyError: continue
                    # df_rev["sort_by"] = df_rev.index.get_level_values(0).map(order_map_cap)
                    # df_rev.sort_values("sort_by", inplace=True)
                    # df_rev.drop(columns="sort_by", inplace=True)
                    for i in FR_rev[scen].index:
                        if i not in techs:
                            techs.append(i)
                    #print(techs)
                    total_rev[scen] = aggregate_in_df(total_rev[scen], wind, "Wind")
                    total_rev[scen] = aggregate_in_df(total_rev[scen], PV, "Solar PV")
                    total_rev[scen] = aggregate_in_df(total_rev[scen], thermals, "thermals")
                    total_rev[scen].drop(CHP, inplace=True, errors='ignore')
                    total_rev[scen] = aggregate_in_df(total_rev[scen], ["RO","RR"], "Hydro")
                    total_rev[scen] = aggregate_in_df(total_rev[scen], PtH, "PtH")
                    total_rev[scen].drop("W_HOB", inplace=True, errors='ignore')
                    # print_red(FR_rev[scen])
                    # print_cyan(total_rev[scen])
                    df_share[flex].loc[(region,year)] = (FR_rev[scen]/total_rev[scen]).round(3)*100
for flex in flexes:
    print_red(flex)
    df_share[flex].fillna(0,inplace=True)
    for region in regions:
        print(region)
        print_green(df_share[flex].loc[region])
        # Plotting the data
for i_t, tech in enumerate(technologies_to_show):
    print_cyan(tech)
    print(df_rev[tech].T)
    df_rev[tech].T.plot(ax=axs[i_t], legend=None, color=['teal', 'teal', 'purple', 'purple', 'orange', 'orange'],
                        marker='o', zorder=-1, style=['-','--']*len(regions)) #, color=color_dict["Battery"]
    markers = ['$L$', '$H$']*len(regions)
    for i_l, line in enumerate(axs[i_t].get_lines()):
        line.set_marker(markers[i_l])
    for i_r, region in enumerate(regions):
        axs[i_t].fill_between(years,df_rev[tech].loc[(region,"lowFlex")],df_rev[tech].loc[(region,"highFlex")], alpha=0.3, color=['teal', 'purple', 'orange'][i_r])
    axs[i_t].set_title(tech_names[tech], fontsize=12)
    axs[i_t].set_xticks([0,1,2,3])
    axs[i_t].set_xticklabels([year_names[int(year)].capitalize() for year in years]) #, rotation=20, ha="center", va="top", rotation_mode='anchor'
if i_r == 0 and False:
    axs[i_r].text(0.1, 0.5, year_names_twolines[year].capitalize(), transform=axs[i_r].transAxes,
                               ha="center", va="center", fontsize=12)
plt.figtext(0,0.5,f"Revenue{' per capacity' if per_cap else ''} [M€/{'GW/' if per_cap else ''}yr]", fontsize=12, rotation=90, va="center",ha="center")
#axs[1].set_ylabel("Revenue [M€/yr]", fontsize=12)

#plt.figtext(0.21, 0.5, "Revenue from reserves [M€/yr]", ha="center", va="center", rotation=90)
#plt.figtext(1.02, 0.5, "Reserve share of total revenue [-]", ha="right", va="center", rotation=90)
lines = [Line2D([0], [0], color=['teal','purple','orange'][i_r], lw=5) for i_r in range(len(regions))]
legend = fig.legend(lines, ["Nordic+","Brit","Iberia"], loc="lower center", bbox_transform=axs[0].transAxes, bbox_to_anchor=(0.5, 1.27), ncol=3)
fig.suptitle(f"Reserve supply revenue{' per installed capacity' if per_cap else ''}", y=1.02, fontsize=13)
plt.tight_layout()
fig_path = f"figures\\"
plt.savefig(fig_path+f"FR_revenue_lines_{timestep}h{'_per_cap' if per_cap else ''}.png", dpi=400, bbox_inches="tight")
#plt.show()
                    #inertia_rev = data[scen]["tech_revenue_inertia"]
                    #FC_inertia = FR_rev+inertia_rev
                    #print_green((FR_rev[scen]/(total_rev[scen])).sort_values(ascending=False)[:10])
                #else:
                    #print_red(total_rev[scen].sort_values(ascending=False)[:10])

