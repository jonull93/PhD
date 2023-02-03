import sys
import os
import pickle
import order_cap
import pandas as pd
import matplotlib.pyplot as plt
from order_cap import wind
from my_utils import print_red, print_green, print_cyan
import mat73

# os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

years = range(1980,2020)

ref_cap = mat73.loadmat(r"C:\Users\jonull\git\python\input\GISdata_solar1980_nordic_L.mat")["capacity_pvplantA"][2,:]
#print(ref_cap)
caps = []
for year in years:
    filename = rf"C:\Users\jonull\git\python\input\old\GISdata_solar{year}_nordic_L.mat"
    caps.append(mat73.loadmat(filename)["capacity_pvplantA"][2,:])

y1 = [i[0] for i in caps]
y2 = [i[1] for i in caps]
plt.plot(years,y1,label="-1")
plt.axhline(ref_cap[0])
plt.plot(years,y2,color="r",label="-2")
plt.axhline(ref_cap[1],color="r")
plt.legend()
plt.show()

file_suffix = ""
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
#timestep = 3
#data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))


def aggregate_in_df(df, index_list: list, new_index: str):
    temp = df.loc[df.index.intersection(index_list)].sum()
    df.drop(index_list, inplace=True, errors='ignore')
    df.loc[new_index] = temp
    return df
