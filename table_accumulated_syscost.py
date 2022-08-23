import os
import pickle
import order_cap
from my_utils import print_red, print_green
from termcolor import colored

# os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

file_suffix = "appended"
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
timestep = 3
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))
regions = ["brit", "iberia", "nordic"]
flexes = ["lowFlex", "highFlex"]
baseFC = "fullFC"
compare = ("FC", ["fullFCnoBat", "fullFCnoWind", "fullFCnoPTH", ])  # ("suffix", "correct_IE_Nminus1")  #
first_year = "2020"
future_years = ["2025", "2030", "2040"]
indicators = {"cost_tot": [], "cost_flexlim": []}
base_scenarios = [f"{reg}_{flex}_{baseFC}_{first_year}{scen_suffix}_{timestep}h" for reg in regions for flex in flexes]
print_green(f"- Comparing {baseFC} to {compare[0]}:{compare[1]} -")
print(",".join(indicators))
for scen in base_scenarios:
    if compare[0] == "FC":
        compscens = [scen.replace(baseFC, s) for s in compare[1]]
    elif compare[0] == "suffix":
        _ = scen.split("_")
        _.insert(-1, compare[1])
        compscens = ["_".join(_)]
    if scen not in data:
        print(scen, "was not found in data")
        continue
    for compscen in compscens:
        if compscen not in data:
            print(compscen,"was not found in data")
            compscens.remove(compscen)
    if len(compscens)==0: continue
    for ind in indicators:
        if "flexlim" in ind:
            indicators[ind] = [data[scen][ind].sum()+sum([data[scen.replace(first_year, year)][ind].sum() for year in future_years])]
            for compscen in compscens:
                indicators[ind].append(data[compscen][ind].sum()+sum([data[compscen.replace(first_year, year)][ind].sum() for year in future_years]))
        else:
            indicators[ind] = [data[scen][ind] + sum([data[scen.replace(first_year, year)][ind] for year in future_years])]
            for compscen in compscens:
                indicators[ind].append(data[compscen][ind] + sum([data[compscen.replace(first_year, year)][ind] for year in future_years]))
    to_print = [f"{scen.replace('_'+baseFC, '').replace(scen_suffix, '').replace('_'+first_year, '')}"]
    for ind, val in indicators.items():
        to_print.append(f"{round(val[0], 3)}")
        for i in range(len(compscens)):
            to_print.append(f"({'+' if val[1+i] - val[0] >= 0 else ''}{round(val[1+i] - val[0], 3)})")
    print(",".join(to_print))

# data["iberia_lowFlex_fullFC_slimSpain_2025_3h"]["gen_per_eltech"]
