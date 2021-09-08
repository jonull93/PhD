import pickle
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import matplotlib.gridspec as gridspec
import os
os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

from my_utils import color_dict, order_cap, add_in_dict, tech_names, scen_names

data_dict = pickle.load(open(r"C:\Users\Jonathan\Box\python\PickleJar\data_results_6h_slowVRE.pickle", "rb"))

scenarios = list(data_dict.keys())
OR_cost = {scenario: [] for scenario in scenarios}
FR_regional_interval_costs = {scenario: [] for scenario in scenarios}
FR_total_interval_costs = {scenario: [] for scenario in scenarios}

for scenario, data in data_dict.items():
    if "noFC" in scenario or "highFlex" in scenario:
        continue
    OR_cost[scenario] = data["OR_cost"]
    FR_regional_interval_costs[scenario] = data["OR_cost"].T.sum()
    FR_total_interval_costs[scenario] = FR_regional_interval_costs[scenario].T.sum(level=[1]).astype(int)
    splits = scenario.split("_")
    print(f"""== {splits[0]} {splits[3]} ==""")
    for ind, i in enumerate(FR_total_interval_costs[scenario]): print(ind+1,":",i)
