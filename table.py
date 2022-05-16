import os
import pickle
import order_cap
from my_utils import print_red, print_green
from termcolor import colored

# os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

file_suffix = "noDoubleUse"
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix
timestep = 3
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))
regions = ["brit", "iberia", "nordic"]
flexes = ["lowFlex"]
baseFC = "fullFC"
compare = ("FC", "fullFC_noDoubleUse")#("suffix", "correct_IE_Nminus1")  # ("FC", "fullFC")
years = [2020, 2025, 2030, 2040]
indicators = {"cost_tot": [], "VRE_share_total": [], "thermal_share_total": [], "curtailment": [], "bat": [],
              "cost_flexlim": [], "FR_binding_hours": 0., "FR_hard_binding_hours": 0., "base_mid_thermal_FLHs": [],
              "peak_thermal_FLHs": [], "FR_share_ESS": [], "FR_share_thermal": [], "FR_share_hydro": [], "FR_share_VRE": [], "FR_share_PtH": []}
base_scenarios = [f"{reg}_{flex}_{baseFC}_{year}{scen_suffix}_{timestep}h" for reg in regions for flex in flexes for year in
                  years]
print_green(f"- Comparing {baseFC} to {compare[0]}:{compare[1]} -")
print(","+",".join(indicators))
for scen in base_scenarios:
    if compare[0] == "FC": compscen = scen.replace(baseFC, compare[1])
    elif compare[0] == "suffix":
        _ = scen.split("_")
        _.insert(-1, compare[1])
        compscen = "_".join(_)
    if scen not in data:
        print(scen, "was not found in data")
        continue
    if compscen not in data:
        print(compscen,"was not found in data")
        continue
    for ind in indicators:
        if "flexlim" in ind:
            indicators[ind] = [data[scen][ind].sum(), data[compscen][ind].sum()]
        elif "bat" in ind:
            try:
                indicators[ind] = [data[scen]["tot_cap"].loc[ind].sum(), data[compscen]["tot_cap"].loc[ind].sum(),
                                   data[scen]["tot_cap"].loc[ind+"_cap"].sum(),
                                   data[compscen]["tot_cap"].loc[ind+"_cap"].sum()]
            except KeyError:
                indicators[ind] = [0, 0, 0, 0]
        elif ind in ["curtailment", "VRE_share_total", "thermal_share_total"]:
            indicators[ind] = [data[scen][ind] * 100, data[compscen][ind] * 100]
        elif ind == "FR_binding_hours":
            indicators[ind] = sum([1 for i in data[compscen]["FR_cost"].sum() if i > 0.5])
        elif ind == "FR_hard_binding_hours":
            indicators[ind] = sum([1 for i in data[compscen]["FR_cost"].sum() if i > 10])
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
            fullFC_techs = [tech for tech in data[compscen]["tot_cap"].groupby(level=0).sum().index if tech in techs]
            try:
                noFC_totalgen = sum([data[scen]["gen_per_eltech"].loc[tech] for tech in noFC_techs if
                                     tech in data[scen]["gen_per_eltech"].index])
            except TypeError:
                noFC_totalgen = data[scen]["gen_per_eltech"].loc[noFC_techs[0]]
            noFC_totalcap = sum([data[scen]["tot_cap"].groupby(level=0).sum().loc[tech] for tech in noFC_techs])
            fullFC_totalgen = sum(
                [data[compscen]["gen_per_eltech"].loc[tech] for tech in fullFC_techs if
                 tech in data[compscen]["gen_per_eltech"].index])
            fullFC_totalcap = sum(
                [data[compscen]["tot_cap"].groupby(level=0).sum().loc[tech] for tech in fullFC_techs])

            try:
                indicators[ind] = [round(noFC_totalgen / noFC_totalcap), round(fullFC_totalgen / fullFC_totalcap)]
            except ZeroDivisionError:
                print_red(scen, techs, noFC_totalcap, fullFC_totalcap, )
                print(noFC_techs, data[scen]["gen_per_eltech"].index)
                print_red(data[scen]["tot_cap"].groupby(level=0).sum())
                print_red(data[compscen]["tot_cap"].groupby(level=0).sum())
                raise
        elif "FR_share" in ind:
            indicators[ind] = [round(data[scen][ind]*100), round(data[compscen][ind]*100)]
        else:
            indicators[ind] = [data[scen][ind], data[compscen][ind]]
    # print(colored(scen, "cyan"))
    to_print = [f"{scen.replace('_noFC', '').replace(scen_suffix, '')}"]
    for ind, val in indicators.items():
        if "bat" in ind:
            to_print.append(
                f"{round(val[0], 2)} / {round(val[2], 2)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 2)} / {'+' if val[3] - val[2] >= 0 else ''}{round(val[3] - val[2], 2)})")
        elif ind in ["curtailment", "VRE_share_total", "thermal_share_total"]:
            to_print.append(f"{round(val[0], 1)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 1)})")
        elif ind in ["FR_binding_hours", "FR_hard_binding_hours"]:
            to_print.append(f"{val*timestep}")
        else:
            to_print.append(f"{round(val[0], 3)} ({'+' if val[1] - val[0] >= 0 else ''}{round(val[1] - val[0], 3)})")
    print(",".join(to_print))

for scen in base_scenarios:
    comp_scen = scen.replace(baseFC, compare[1])
    try: bat = data[comp_scen]["tot_cap"]["bat_PS"].sum()
    except KeyError: bat = 0
    try: bat_cap = data[comp_scen]["tot_cap"]["bat_cap_PS"].sum()
    except KeyError: bat_cap = 0
    print(f"0 / 0 (+{round(bat, 2)} / +{round(bat_cap, 2)})")
# data["iberia_lowFlex_fullFC_slimSpain_2025_3h"]["gen_per_eltech"]
