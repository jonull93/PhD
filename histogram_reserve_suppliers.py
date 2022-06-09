import pickle
import pandas as pd
import matplotlib.pyplot as plt
from my_utils import print_red, print_green, print_cyan

picklefile = "data_results_3h_appended.pickle"
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix

timestep = 3
if timestep > 1:
    timestep = f"_{timestep}h"
else:
    timestep = ""

regions = ["brit", "iberia", "nordic"]
years = [2020, 2025, 2030, 2040]
flex = "lowFlex"
FC = "fullFC"

histogram_techs = ["bat_cap", "EB", "HP", "electrolyser"]

data = pickle.load(open(rf"PickleJar/{picklefile}", "rb"))
for tech in histogram_techs:
    fig, axes = plt.subplots(4,3, sharex=False, sharey=False)
    for i_r,year in enumerate(years):
        axes[i_r][0].text(-0.45,0.5,f"{year}:",fontdict={"fontsize":"12", "transform":axes[i_r][0].transAxes,
                                                        "horizontalalignment":'right', "verticalalignment":'center'})
        for i_c,region in enumerate(regions):
            if i_r==0: axes[i_r][i_c].set_title(region.capitalize())
            scenario = f"{region}_{flex}_{FC}_{year}{scen_suffix}{timestep}"
            try: tech_usage = data[scenario]["gen"].sum(axis=0,level=0).loc[tech]
            except KeyError: tech_usage = [0]
            axes[i_r][i_c].hist(tech_usage)
    axes[3][1].text(0.5, -0.5, 'Gen [GW]', fontdict={"transform":axes[3][1].transAxes, "horizontalalignment":'center',
                                                      "verticalalignment":'top'})
    fig.text(0.12, 0.5, 'Usage [hr]', va='center', rotation='vertical')
    plt.tight_layout()
    plt.savefig(rf"figures\histogram_{tech}.png", dpi=300)

