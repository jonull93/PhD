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

years = [2020,2025,2030,2040]
regions = ["nordic", "brit", "iberia"]
h = 3
flex = "lowFlex"
#fig, axes = plt.subplots(nrows=1, ncols=4, figsize=(8, 3))
FR_demand_6 = pd.DataFrame(columns=pd.MultiIndex(levels=[[],[]],
                      codes=[[],[]],
                      names=['Year','Region']))
for i_y, year in enumerate(years):
    for region in regions:
        scen = f"{region}_{flex}_fullFC_{year}_{h}h"
        FR_demand_6[year, region] = data[scen]["FR_demand"]["total"].loc[:, '6', :].sum(axis=0)
    print(FR_demand_6)
#    plt.sca(axes[i_y])
#    plt.ylim([0,30])
plt.boxplot(FR_demand_6, whis=(1,99), sym="x")
plt.ylim(0,30)
axes = plt.gca()
axes.yaxis.grid()
xregions = [r.capitalize() for r in regions]*4
plt.xticks(range(1,len(FR_demand_6.columns)+1), xregions)
for i in range(len(FR_demand_6.columns)+1): #draw seperating lines between xlabels
    x = [i+0.5]*2
    if i%3==0:
        y = [0, -3.5]
        plt.plot(x,y,clip_on=False,color="black",linewidth=1)
        plt.plot(x, axes.get_ylim(), clip_on=False, color="grey", linewidth=0.5, ls=(15,(5,20)))
        if i<len(FR_demand_6.columns):
            plt.text(i+2, -3.5, years[int(i/3)], fontsize=12, ha="center")
plt.ylabel("Frequency reserve demand [GW]")
plt.title(f"Reserve demand, {flex}")
plt.tight_layout()
plt.savefig(rf"figures\FR_demand_boxplot_{h}h.png", dpi=600)
plt.savefig(rf"figures\FR_demand_boxplot_{h}h.pdf")
#plt.show()
#print(data["brit_lowFlex_fullFC_2030_3h"]["FR_demand"])