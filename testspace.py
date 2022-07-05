import sys
import os
import pickle
import order_cap
import pandas as pd
from my_utils import print_red, print_green, print_cyan

# os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

file_suffix = ""
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
timestep = 6
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))

size = {}
for key in data:
    #print(f"{key} takes up {sys.getsizeof(data[key])} bytes")
    for key2 in data[key]:
        #print(f"{key2} takes up {sys.getsizeof(data[key][key2])} bytes")
        size[key2] = sys.getsizeof(data[key][key2])
    break

size_s = pd.Series(data=size.values(), index=size.keys())
#print(size_s.sort_values(ascending=False)[:10])

total_rev = {}
FR_rev = {}
for region in ["nordic", "brit", "iberia"]:
    for flex in ["lowFlex", "highFlex"]:
        for FC in ["noFC", "fullFC"]:
            for year in [2020, 2025, 2030, 2040]:
                scen = f"{region}_{flex}_{FC}_{year}_{timestep}h"
                print_cyan(scen)
                #scen = "nordic_lowFlex_fullFC_2025_6h"
                total_rev[scen] = data[scen]["tech_revenue"]
                PtH = ["EB", "HP"]
                if "fullFC" in FC:
                    FR_rev[scen] = data[scen]["tech_revenue_FR"]
                    #inertia_rev = data[scen]["tech_revenue_inertia"]
                    #FC_inertia = FR_rev+inertia_rev
                    print_green((FR_rev[scen]/(total_rev[scen])).sort_values(ascending=False)[:10])
                #else:
                    #print_red(total_rev[scen].sort_values(ascending=False)[:10])

fig_scen = "nordic_lowFlex_fullFC_2025_6h"
