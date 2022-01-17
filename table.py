import os
import pickle
import order_cap
from my_utils import print_red
from termcolor import colored

# os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

suffix = "noGpeak"
if len(suffix) > 0: suffix = "_" + suffix
timestep = 3
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{suffix}.pickle"), "rb"))
regions = ["brit", "iberia", "nordic"]
flexes = ["lowFlex",]
FC = ["noFC", "fullFC"]
years = [2020, 2025, 2030, 2040]
indicators = {"cost_tot": [], "VRE_share_total": [], "thermal_share_total": [], "curtailment": [], "bat": [],
              "cost_flexlim": [], "FR_binding_hours": 0., "base_mid_thermal_FLHs": [], "peak_thermal_FLHs": []}
print(list(indicators.keys()))
base_scenarios = [f"{reg}_{flex}_noFC_{year}{suffix}_{timestep}h" for reg in regions for flex in flexes for year in years]
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
        elif ind in ["curtailment", "VRE_share_total", "thermal_share_total"]:
            indicators[ind] = [data[scen][ind]*100, data[scen.replace("noFC", "fullFC")][ind]*100]
        elif ind == "FR_binding_hours":
            indicators[ind] = sum([1 for i in data[scen.replace("noFC", "fullFC")]["FR_cost"].sum() if i>10])
        elif "thermal_FLH" in ind:
            techs = []
            if "mid" in ind:
                techs += order_cap.midload
                techs += order_cap.CCS
                techs += order_cap.CHP
            if "base" in ind:
                techs += order_cap.baseload
            if "peak" in ind:
                techs += order_cap.peak
            noFC_techs = [tech for tech in data[scen]["tot_cap"].groupby(level=0).sum().index if tech in techs]
            fullFC_techs = [tech for tech in data[scen.replace("noFC", "fullFC")]["tot_cap"].groupby(level=0).sum().index if tech in techs]
            try:
                noFC_totalgen = sum([data[scen]["gen_per_eltech"].loc[tech] for tech in noFC_techs if tech in data[scen]["gen_per_eltech"].index])
            except TypeError:
                noFC_totalgen = data[scen]["gen_per_eltech"].loc[noFC_techs[0]]
            noFC_totalcap = sum([data[scen]["tot_cap"].groupby(level=0).sum().loc[tech] for tech in noFC_techs])
            fullFC_totalgen = sum(
                [data[scen.replace("noFC", "fullFC")]["gen_per_eltech"].loc[tech] for tech in fullFC_techs if tech in data[scen.replace("noFC", "fullFC")]["gen_per_eltech"].index])
            fullFC_totalcap = sum(
                [data[scen.replace("noFC", "fullFC")]["tot_cap"].groupby(level=0).sum().loc[tech] for tech in fullFC_techs])

            try: indicators[ind] = [noFC_totalgen/noFC_totalcap, fullFC_totalgen/fullFC_totalcap]
            except ZeroDivisionError:
                print_red(scen, techs, noFC_totalcap, fullFC_totalcap, )
                print(noFC_techs, data[scen]["gen_per_eltech"].index)
                print_red(data[scen]["tot_cap"].groupby(level=0).sum())
                print_red(data[scen.replace("noFC", "fullFC")]["tot_cap"].groupby(level=0).sum())
                raise
        else:
            indicators[ind] = [data[scen][ind], data[scen.replace("noFC", "fullFC")][ind]]
    #print(colored(scen, "cyan"))
    to_print = [f"{scen.replace('_noFC','').replace(suffix,'')}"]
    for ind, val in indicators.items():
        if "bat" in ind:
            to_print.append(f"{round(val[0], 2)} / {round(val[2], 2)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 2)} / {'+' if val[3] - val[2] >= 0 else ''}{round(val[3] - val[2], 2)})")
        elif ind in ["curtailment", "VRE_share_total", "thermal_share_total"]:
            to_print.append(f"{round(val[0], 1)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 1)})")
        elif ind == "FR_binding_hours":
            to_print.append(f"{val} ({val*3})")
        else:
            to_print.append(f"{round(val[0], 3)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 3)})")
    print(",".join(to_print))
