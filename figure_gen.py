import pickle
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import matplotlib.gridspec as gridspec
import os
#os.chdir(r"C:\Users\Jonathan\git\python")  # not needed unless running line-by-line in a console
from my_utils import TECH, color_dict, order_map_gen, add_in_dict, tech_names, print_red, print_cyan, print_green, year_names, scen_names

WON = ["WON"+a+str(b) for a in ["A","B"] for b in range(1, 6)]
PV = ["PVPA1", "PVPB1", "PVR1"]


def del_first(list, to_delete, mirror_list=False):
    if list.count(to_delete) > 1:
        for i,item in enumerate(list):
            if item == to_delete:
                #print("Removed item nr",i,f"'{to_delete}'")
                del list[i]
                if mirror_list: del mirror_list[i]
                break
    return list, mirror_list


def df_to_stacked_areas(scen_data, ax, to_drop=None, region=None, startday=1, days=7, sum_VRE=True, bat_SoC=True, FR=True, expect_battery=True):
    df = scen_data["gen"].copy()
    timesteps = scen_data["gams_timestep"]
    if to_drop is None:
        to_drop = ["bat", "electrolyser"]
        # doing it this round-about way ensures that changing the patterns/years for one function-call won't linger
        # in the next function call (google "Default arguments value is mutable")
    if bat_SoC:
        try:
            bat = df.loc["bat"]
            bat = bat.sum()
            bat = bat.rename("Bat. storage")
        except Exception as e:
            if expect_battery: print_red("Could not find battery")
            bat_SoC = False
    if FR:
        try:
            FR_price = scen_data["FR_cost"].sum().reindex(list(df),fill_value=0).rename("FR cost")
            FFR_price = scen_data["FR_cost"].groupby(level=1).sum().loc["1"].reindex(list(df), fill_value=0).rename("FFR cost")
        except AttributeError:
            FR = False

    df.drop(to_drop, axis=0, inplace=True, errors='ignore')
    # sum regions if region=None, else filter out regions that arent 'region'
    if region is None:
        df = df.groupby(level=0).sum()
    elif type(region) == str:
        df = df.loc[:, region]
    # find indexes that correspond to startday and startday+days
    if type(startday) == int:
        for i, t in enumerate(timesteps):
            if str(startday) in t and "start" not in locals():
                start = i
            if str(startday+days) in t:
                end = i
                break
    # combine VRE rows if sum_VRE=True
    if sum_VRE:
        WON_rows = [i for i in df.T.columns if i in WON]
        PV_rows = [i for i in df.T.columns if i in PV]
        summed_WON = df.loc[WON_rows].sum(axis=0).rename("WON")
        summed_PV = df.loc[PV_rows].sum(axis=0).rename("PV")
        df.drop(WON_rows, inplace=True)
        df.drop(PV_rows, inplace=True)
        df = df.append(summed_PV)
        df = df.append(summed_WON)
    if expect_battery:
        bat_discharge = df.loc["bat_cap"].clip(lower=0).rename("Bat. Out")
        bat_charge = df.loc["bat_cap"].clip(upper=0).rename("Bat. In")
        df = df.append(bat_charge)
        df = df.append(bat_discharge)
    try:
        df.loc["EB"] = -df.loc["EB"]
        df.loc["HP"] = -df.loc["HP"]
    except KeyError as e:
        print_red(f"Failed to access PtH stuff")
    df["sort_by"] = df.index.get_level_values(0).map(order_map_gen)
    df.sort_values("sort_by", inplace=True)
    try: df.drop("bat_cap",inplace=True)
    except KeyError: None
    df.drop(columns="sort_by", inplace=True)
    to_plot = df.iloc[:, start:end].T
    plotted_techs = list(to_plot.columns)
    techs = to_plot.columns
    colors = [color_dict[tech] for tech in techs]
    #print(f"Techs:\n{techs}\nColors:\n{colors}")
    to_plot.plot(kind="area", ax=ax, linewidth=0.1, color=colors)  # plotting
    if bat_SoC: bat.iloc[start:end].plot(kind="line", ax=ax, linewidth=1, color="k")
    curtailment = df.clip(lower=0).sum().add(scen_data["curtailment_profile_total"].sum(), fill_value=0).rename("Load + curt.")
    curtailment.iloc[start:end].plot(kind="line", ax=ax, linewidth=1)
    if FR:
        FR_price.iloc[start:end].plot(kind="line", ax=ax, linewidth=1, secondary_y=True)
        FFR_price.iloc[start:end].plot(kind="line", ax=ax, linewidth=1, secondary_y=True)
    ymax = np.ceil(df.clip(lower=0).sum().max()/5)*5
    ymin = np.floor(df.min().min()/5)*5
    plt.sca(ax)
    plt.xticks(ticks=np.arange(days*24/timestep,step=24/timestep), labels=np.arange(int(to_plot.index[0][1:4]), int(to_plot.index[-1][1:4])+1))
    plt.xlabel("Day")
    handles, labels = ax.get_legend_handles_labels()
    if FR:
        handles2, labels2 = ax.right_ax.get_legend_handles_labels()
        handles += handles2
        labels += labels2
        #print(labels2, labels)
    #plt.legend(loc=6, bbox_to_anchor=(1.01, 0.5))
    ax.set_ylim([ymin, ymax])
    return df, handles, labels, bat_SoC


timestep = 3
years = [2020, 2025, 2030, 2040]
regions = ["nordic", "iberia", "brit"]
modes = ["lowFlex"]
file_suffix = "appended"
if len(file_suffix) > 0 and file_suffix[0] != "_": file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0 and scen_suffix[0] != "_": scen_suffix = "_" + scen_suffix
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))

for region in regions:
    for mode in modes:
        for year in years:
            scenario = f"{region}_{mode}_FC_{year}{scen_suffix}_{timestep}h"
            stripped_scenario = scenario.replace("_FC", "")
            print_cyan(stripped_scenario)
            fig_path = f"figures\\{stripped_scenario}\\"
            os.makedirs(fig_path, exist_ok=True)
            for day in range(1, 358, 28):
                print(f"Days {day} - {day+6}")
                fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(6, 7))
                fig.suptitle(f"Generation during Week {int(np.ceil(day/7))} in {region.capitalize()}{', HighFlex' if 'high' in mode else ''}, {year_names[year]}")
                fig.text(-0.02, 0.5, 'Electricity generation and storage level [GWh(/h)] ', va='center', rotation='vertical')
                fig.text(0.99, 0.5, 'Reserve price [€-cents/MWh] ', va='center',
                         rotation='vertical')
                handles = []
                labels = []
                for i, FC in enumerate(["noFC", "fullFC"]):
                    current_scenario = scenario.replace("_FC", f"_{FC}")
                    df, handles_, labels_, bat = df_to_stacked_areas(data[current_scenario], axes[i],
                                                                     startday=day, expect_battery=year>2020)
                    axes[i].set_title(scen_names[FC])
                    handles += handles_
                    labels += labels_
                    axes[i].get_legend().remove()
                #print_green(labels)
                labels, handles = del_first(labels, 'Load + curt.', mirror_list=handles) # delete first
                labels, handles = del_first(labels, 'Bat. storage', mirror_list=handles)
                #print_green(labels)
                _len = len(labels)
                _len2 = len(handles)
                if _len != _len2: raise ArithmeticError
                for i_l, label in enumerate(labels[::-1], start=1):  # removing duplicates
                    if label in labels[:_len-i_l]:
                        del labels[_len-i_l]
                        del handles[_len - i_l]
                print("labels without duplicates, before reordering:\n", labels)

                labels_to_legend = []
                handles_to_legend = []
                # print(labels)
                for tech in order_map_gen:
                    if tech in labels:
                        if tech in tech_names:
                            labels_to_legend.append(tech_names[tech])
                        else:
                            labels_to_legend.append(tech)
                            print_red(tech, "missing from tech_names")
                        tech_index = labels.index(tech)
                        handles_to_legend.append(handles[tech_index])
                #print_cyan("ordered labels:",labels_to_legend)
                unused_labels = []
                for tech in labels:
                    if tech not in labels_to_legend and (tech in tech_names and tech_names[tech] not in labels_to_legend):
                        unused_labels.append(tech)
                    #if (tech in tech_names and tech_names[tech] not in labels_to_legend) and tech not in ["Load", "FR cost", "FFR cost", "Bat. storage", "Bat. In", "Bat. Out"]:
                    #    print_red(f"did not find {tech} in order_gen!")
                if len(unused_labels)>0: print_red(f"These labels got filtered out: {unused_labels}")
                labels_to_legend += labels[-3:]
                #print("ordered and appended labels:\n",labels_to_legend)
                handles_to_legend += handles[-3:]
                labels_to_legend.reverse()
                handles_to_legend.reverse()
                fig.tight_layout()
                fig.legend(handles_to_legend,labels_to_legend,bbox_to_anchor=(1.03, 0.5), ncol=1, loc="center left")
                plt.savefig(fig_path+f"week {int(np.ceil(day/7))}.png", dpi=300, bbox_inches='tight')
                plt.savefig(fig_path+f"week {int(np.ceil(day/7))}.eps", bbox_inches="tight", format="eps")
                plt.close(fig)
print(labels)
