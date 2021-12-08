import pickle
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import matplotlib.gridspec as gridspec
import os
#os.chdir(r"C:\Users\Jonathan\git\python")  # not needed unless running line-by-line in a console
from my_utils import TECH, color_dict, order_map_gen, add_in_dict, tech_names, scen_names

WON = ["WON"+a+str(b) for a in ["A","B"] for b in range(1, 6)]
PV = ["PVPA1", "PVPB1", "PVR1"]


def df_to_stacked_areas(scen_data, ax, to_drop=None, region=None, startday=1, days=7, sum_VRE=True, bat_SoC=True, FR=True):
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
            print(df)
            bat_SoC = False
    if FR:
        try:
            FR_price = scen_data["FR_cost"].sum().reindex(list(df),fill_value=0).rename("FR price")
            FFR_price = scen_data["FR_cost"].sum(level=1).loc["1"].reindex(list(df), fill_value=0).rename("FFR price")
        except AttributeError:
            FR = False


    df.drop(to_drop, axis=0, inplace=True, errors='ignore')

    # sum regions if region=None, else filter out regions that arent 'region'
    if region is None:
        df = df.sum(level=0, axis=0)
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
        print(f"Timesteps {start} - {end}")
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
    try:
        bat_discharge = df.loc["bat_cap"].clip(lower=0).rename("Bat. Out")
        bat_charge = df.loc["bat_cap"].clip(upper=0).rename("Bat. In")
        df.loc["EB"] = -df.loc["EB"]
        df.loc["HP"] = -df.loc["HP"]
        df = df.append(bat_charge)
        df = df.append(bat_discharge)
    except KeyError:
        None

    df["sort_by"] = df.index.get_level_values(0).map(order_map_gen)
    df.sort_values("sort_by", inplace=True)
    try: df.drop("bat_cap",inplace=True)
    except KeyError: None
    df.drop(columns="sort_by", inplace=True)
    df.iloc[:, start:end].T.plot(kind="area", ax=ax, linewidth=0.1)  # plotting
    curtailment = df.clip(lower=0).sum().add(scen_data["curtailment_profile_total"].sum(), fill_value=0).rename("Load")
    curtailment.iloc[start:end].plot(kind="line", ax=ax, linewidth=1)
    if bat_SoC: bat.iloc[start:end].plot(kind="line", ax=ax, linewidth=1, color="k")
    if FR:
        FR_price.iloc[start:end].plot(kind="line", ax=ax, linewidth=1)
        FFR_price.iloc[start:end].plot(kind="line", ax=ax, linewidth=1)
    ymax = np.ceil(df.clip(lower=0).sum().max()/5)*5
    ymin = np.floor(df.min().min()/5)*5
    plt.legend(loc=6, bbox_to_anchor=(1.01, 0.5))
    ax.set_ylim([ymin, ymax])
    return df


timestep = 6
year = 2040
region = "brit"
mode = "lowFlex"
FC = "noFC"
pickle_suff = ""
if len(pickle_suff) > 0: pickle_suff = "_" + pickle_suff
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{pickle_suff}.pickle"), "rb"))

scenario = f"{region}_{mode}_{FC}_{year}_{timestep}h"
fig_path = f"figures\\{scenario}\\"
os.makedirs(fig_path, exist_ok=True)
for day in range(1, 358, 28):
    fig, ax = plt.subplots()
    plt.title(f"{region.capitalize()} {mode}, {FC}")
    df = df_to_stacked_areas(data[scenario], ax, startday=day)
    plt.savefig(fig_path+f"week {int(np.ceil(day/7))}.png", dpi=300, bbox_inches='tight')
