import sys
import os
import pickle
import order_cap
import pandas as pd
import matplotlib.pyplot as plt
from order_cap import wind
from my_utils import print_red, print_green, print_cyan

file_suffix = ""
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
timestep = 3
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))

years = [2020,2025,2030,2040]
regions = ["nordic", "brit", "iberia"]
flexes = ["lowFlex","highFlex"]

for flex in flexes:
    print_red(flex)
    print(f"{years[0]:14}{years[1]:7}{years[2]:7}{years[3]:7}")
    for region in regions:
        l = []
        #print_cyan(f"{region.capitalize()}: {flex}")
        for year in years:
            scen = f"{region}_{flex}_fullFC_{year}_{timestep}h"
            reserve_prices = data[scen]["FR_cost"]
            reserve_amount = data[scen]["FR_demand"]
            l.append(round((reserve_amount["total"]*reserve_prices).sum().sum()))
        print(f"{region:<7}{l[0]:7}{l[1]:7}{l[2]:7}{l[3]:7}")
