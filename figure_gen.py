import pickle
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import matplotlib.gridspec as gridspec
import os
os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

from my_utils import color_dict, order_map_gen, add_in_dict, tech_names, scen_names

pickleJar = ""
data = pickle.load(open(r"C:\Users\Jonathan\Box\python\PickleJar\data_results_6h.pickle", "rb"))

def df_to_stacked_areas(scen_data, to_drop=None, region=None, startday=1, days=7):
    df = scen_data["gen"]
    timesteps = scen_data["gams_timestep"]
    if to_drop is None:
        to_drop = ["bat", "electrolyser"]
        # doing it this round-about way ensures that changing the patterns/years for one function-call won't linger
        # in the next function call (google "Default arguments value is mutable")
    df.drop(to_drop, axis=0, inplace=True)

    if region is None:
        df = df.sum(level=0, axis=0)
    elif type(region) == str:
        df = df.loc[:, region]

    if type(startday) == int:
        for i, t in enumerate(timesteps):
            if str(startday) in t and "start" not in locals():
                start = i
            if str(startday+days) in t:
                end = i
                break
        print(start,end)

    bat_discharge = df.loc["bat_cap"].clip(lower=0).rename("bat_dis")
    df.loc["bat_cap"] = bat_discharge
    df["sort_by"] = df.index.get_level_values(0).map(order_map_gen)
    df.sort_values("sort_by", inplace=True)
    df.drop(columns="sort_by", inplace=True)
    df.iloc[:, start:end].T.plot(kind="area")
    return df


scenario = "iberia_lowFlex_noFC_2030_6h"
df = df_to_stacked_areas(data[scenario])
plt.show()
