import sys
import os
import pickle
import order_cap
import pandas as pd
import matplotlib.pyplot as plt
from order_cap import wind
from my_utils import print_red, print_green, print_cyan

# os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

file_suffix = ""
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
timestep = 3
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


def aggregate_in_df(df, index_list: list, new_index: str):
    temp = df.loc[df.index.intersection(index_list)].sum()
    df.drop(index_list, inplace=True, errors='ignore')
    df.loc[new_index] = temp
    return df

scen = "nordic_lowFlex_fullFC_2030_3h"
#gen = data[scen]["gen"]
#gen = aggregate_in_df(gen,wind,"Wind")
#for key in data[scen].keys():
#    print(key)
#print(data[scen]["FR_demand"]["total"])
FR_demand_6 = pd.DataFrame()
FR_demand_6 = data[scen]["FR_demand"]["total"].loc[:, '6', :].sum(axis=0)
print(FR_demand_6)
plt.boxplot(FR_demand_6)
#plt.xticks(range(1,len(FR_demand_6.index)+1), FR_demand_6.index)
plt.show()