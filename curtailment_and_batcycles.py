import os
import pickle

from my_utils import print_cyan, print_green, print_red

timestep = 3
suffix = "noGpeak"
if len(suffix) > 0: suffix = "_" + suffix
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{suffix}.pickle"), "rb"))

regions = ["iberia", "brit", "nordic"]
years = [2020, 2025, 2030, 2040]
scenarios = [f"{reg}_lowFlex_fullFC_2040_noGpeak_3h" for reg in regions]

for reg in regions:
    print_green(f"-- {reg.capitalize()} --")
    for year in years:
        print_cyan(year)
        scen = f"{reg}_lowFlex_fullFC_{year}_noGpeak_3h"
        print(" - Curtailment -")
        curt = data[scen]["curtailment_profile_total"].sum().clip(lower=1e-6).round(2)
        weekly_curt = [round(sum(curt.iloc[i:i + 56])) for i in range(0, 2910, 56)]
        tot_curt = round(sum(curt))
        max_curt = curt.max()
        print(f"{tot_curt} GWh of total curtailment")
        print(f"{max_curt} is the highest hourly curtailment, at timestep {curt.idxmax()}")
        print(f"{sum([1 for i in weekly_curt if i < 3])} weeks of =<2 GWh curtailment")
        print("- Battery cycles -")
        if year > 2020:
            bat = data[scen]["gen"].loc[("bat", slice(None))]
            for subreg in bat.index:
                regbat = bat.loc[subreg]
                zeroes = regbat.index[regbat == 0]
                try: regcurt = data[scen]["curtailment_profile_total"].loc[subreg]
                except Exception as e: print_red(e, data[scen]["curtailment_profile_total"])

    print("")
