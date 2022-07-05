import sys
import os
import pickle
import order_cap
import pandas as pd
from my_utils import print_red, print_green
from termcolor import colored

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

scen = "nordic_lowFlex_fullFC_2025_6h"
total_rev = data[scen]["tech_revenue"]
PtH = ["EB", "HP"]
FR_rev = data[scen]["tech_revenue_FR"]
#inertia_rev = data[scen]["tech_revenue_inertia"]
#FC_inertia = FR_rev+inertia_rev
print((FR_rev/(total_rev)).sort_values(ascending=False)[:10])
