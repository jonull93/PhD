import os
import pickle

import pandas as pd

from my_utils import print_cyan, print_green, print_red

timestep = 3
file_suffix = "appended"
if len(file_suffix) > 0: file_suffix = "_" + file_suffix
data = pickle.load(open(os.path.relpath(rf"PickleJar\data_results_{timestep}h{file_suffix}.pickle"), "rb"))
scen_suffix = ""
if len(scen_suffix) > 0: scen_suffix = "_" + scen_suffix


regions = ["iberia", "brit", "nordic"]
years = [2020, 2025, 2030, 2040]
#scenarios = [f"{reg}_lowFlex_fullFC_2040_3h" for reg in regions]
#scenarios = [s for s in scenarios if s in data]

for reg in regions:
    print('\x1b[1;30;43m' + f"-- {reg.capitalize()} --" + '\x1b[0m')
    for year in years:
        print_green(year)
        scen = f"{reg}_lowFlex_noFC_{year}{scen_suffix}_3h"
        FCscen = f"{reg}_lowFlex_fullFC_{year}{scen_suffix}_3h"
        if scen not in data: continue
        print_cyan(" - Curtailment -")
        curt = data[scen]["curtailment_profile_total"].sum().clip(lower=1e-6).round(2)
        weekly_curt = [round(sum(curt.iloc[i:i + 56])) for i in range(0, 2910, 56)]
        tot_curt = round(sum(curt))
        max_curt = curt.max()
        print(f"{tot_curt} GWh of total curtailment")
        print(f"{max_curt} is the highest hourly curtailment, at timestep {curt.idxmax()}")
        print(f"{sum([1 for i in weekly_curt if i < 3])} weeks of =<2 GWh curtailment")
        if year > 2020:
            print_cyan("- Battery cycles -")
            bat = data[scen]["gen"].loc[("bat", slice(None))]
            bat_discharge = data[scen]["discharge"].loc[("bat", slice(None))]
            cycle_length = {}
            for subreg in bat.index:
                regbat = bat.loc[subreg]
                regdischarge = bat_discharge.loc[subreg].level
                bat_size = max(regbat)
                zeroes = regbat.index[regbat == 0]
                regcurt = data[scen]["curtailment_profile_total"].loc[subreg]
                tot_discharge = regdischarge.sum()
                cycles = tot_discharge/bat_size
                cycle_length[subreg] = round(cycles/bat_size)
            print(f"Bat size: {data[scen]['bat']}")
            print(f"Average cycle lengths: {cycle_length} hours")
        if FCscen not in data: continue
        print_cyan("- FR analysis -")
        FR_cost = data[FCscen]["FR_cost"].sum()
        net_load = data[FCscen]["net_load"].sum()
        el_price = data[FCscen]["el_price"].sum()
        highest_el_price = el_price.nlargest(25)
        for ep in highest_el_price:
            el_price.replace(to_replace=ep, value=highest_el_price[-1], inplace=True)
        highest_FR_cost = FR_cost.nlargest(2)
        FR_cost.replace(to_replace=highest_FR_cost[0], value=highest_FR_cost[1], inplace=True)
        weekly_FR_cost = pd.Series([round(sum(FR_cost.iloc[i:i + 56])) for i in range(0, 2910, 56)])
        weekly_net_load = pd.Series([round(sum(net_load.iloc[i:i + 56])) for i in range(0, 2910, 56)])
        weekly_el_price = pd.Series([round(sum(el_price.iloc[i:i + 56])) for i in range(0, 2910, 56)])
        FR_net_load_corr = round(FR_cost.corr(net_load), 2)
        FR_el_price_corr = round(FR_cost.corr(el_price), 2)
        weekly_FR_net_load_corr = round(weekly_FR_cost.corr(weekly_net_load), 2)
        weekly_FR_el_price_corr = round(weekly_FR_cost.corr(weekly_el_price), 2)
        monthly_FR_cost = [round(sum(FR_cost[f"d{i*30:03}a":f"d{i*30+30:03}a"])) for i in range(12)]
        seasonal_FR_cost = {"winter": round(sum(FR_cost[f"d335a":])+sum(FR_cost[:f"d061a"])),  # 91 days
                            "spring": round(sum(FR_cost[f"d061a":f"d152a"])),  # 91 days
                            "summer": round(sum(FR_cost[f"d152a":f"d243a"])),  # 91 days
                            "fall": round(sum(FR_cost[f"d243a":f"d334a"])),  # 91 days
                            }
        print(seasonal_FR_cost)
        print("Correlation between hourly FR cost and net load:", FR_net_load_corr)
        print("Correlation between weekly FR cost and net load:", weekly_FR_net_load_corr)
        print("Correlation between hourly FR cost and elec price:", FR_el_price_corr)
        print("Correlation between weekly FR cost and elec price:", weekly_FR_el_price_corr)
        binding_hours = FR_cost[FR_cost>1]
        nr_binding_hours = binding_hours.sum()
    print("")
