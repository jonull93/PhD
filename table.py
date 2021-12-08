import os
import pickle

from termcolor import colored

# os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console


data = pickle.load(open(os.path.relpath(r"PickleJar\data_results_6h.pickle"), "rb"))
regions = ["brit", "iberia", "nordic"]
flexes = ["lowFlex", "highFlex"]
FC = ["noFC", "fullFC"]
years = [2020, 2025, 2030, 2040]
indicators = {"cost_tot": [], "VRE_share_total": [], "curtailment": [], "bat": [], "cost_flexlim": []}
base_scenarios = [f"{reg}_{flex}_noFC_{year}_6h" for reg in regions for flex in flexes for year in years]
for scen in base_scenarios:
    for ind in indicators:
        if "flexlim" in ind:
            indicators[ind] = [data[scen][ind].sum(), data[scen.replace("noFC", "fullFC")][ind].sum()]
        elif "bat" in ind:
            try:
                indicators[ind] = [data[scen]["tot_cap"].loc["bat"].sum(), data[scen.replace("noFC", "fullFC")]["tot_cap"].loc["bat"].sum(),
                                   data[scen]["tot_cap"].loc["bat_cap"].sum(),
                                   data[scen.replace("noFC", "fullFC")]["tot_cap"].loc["bat_cap"].sum()]
            except KeyError: indicators[ind] = [0,0,0,0]
        elif ind in ["curtailment", "VRE_share_total"]:
            indicators[ind] = [data[scen][ind]*100, data[scen.replace("noFC", "fullFC")][ind]*100]
        else:
            indicators[ind] = [data[scen][ind], data[scen.replace("noFC", "fullFC")][ind]]
    #print(colored(scen, "cyan"))
    to_print = []
    for ind, val in indicators.items():
        if "bat" in ind:
            to_print.append(f"{round(val[0], 2)} / {round(val[2], 2)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 2)} / {'+' if val[3] - val[2] >= 0 else ''}{round(val[3] - val[2], 2)})")
        elif ind in ["curtailment", "VRE_share_total"]:
            to_print.append(f"{round(val[0], 1)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 1)})")
        else:
            to_print.append(f"{round(val[0], 3)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 3)})")
    print(",".join(to_print))
