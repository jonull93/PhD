import pickle
import pandas as pd
import matplotlib.pyplot as plt
from my_utils import print_red, print_green, print_cyan
import tabulate


def test1():
    data = pickle.load(open(r"C:\git\quality-of-life-scripts\PickleJar\data_results_3h.pickle", "rb"))
    scen = "nordic_lowFlex_noFC_2020_3h"
    cap = data[scen]["tot_cap"].loc[slice(None), "SE_S"]
    cap.drop("HP", inplace=True)
    var_cost = {"H_CHP": 30, "G": 75, "G_CHP": 65, "G_peak": 140, "W": 40, "W_CHP": 35, "WA_CHP": 5, "U": 5, "WG_peak": 200,
                "RO": 45}
    for tech in cap.index:
        if "WO" in tech or "PV" in tech:
            var_cost[tech] = 1

    var_cost_df = pd.DataFrame.from_dict(var_cost, orient="index", columns=["var_cost"])
    cap = var_cost_df.join(pd.DataFrame(cap, columns=["cap"]))
    cap.sort_values(by="var_cost", inplace=True)
    cap["cumcap"] = cap["cap"].cumsum()
    print(cap)
    plt.plot(cap["cumcap"], cap["var_cost"])
    plt.text(3.3, 5, "VRE")
    plt.text(9, 8, "Nuclear")
    plt.text(17, 45, "Thermals\n& Hydro", bbox=dict(facecolor='white', alpha=0.5, edgecolor="none", pad=2))
    plt.xlabel("Power [GW]")
    plt.ylabel("Price [€/MWh]")
    plt.plot([11,16,16.2,22.4],[200, 170, 10, 5])
    plt.text(9.3, 170, "High-price\naverse consumers")
    plt.text(14.5, 100, "Regular\nconsumers", bbox=dict(facecolor='white', alpha=0.5, edgecolor="none", pad=2))
    plt.text(17.5, 14, "Opportunistic\nconsumption")
    plt.legend(["Supply", "Demand"])
    plt.title("Example of supply-and-demand in electricity market")
    plt.tight_layout()
    plt.savefig("figures\\supply_and_demand.png",dpi=400,)
    plt.show()


def test2():
    pickle_files = ["data_results_3h", "data_results_3h_base", "data_results_3h_appended"]
    df = pd.DataFrame(columns=["sys_cost"], index=pd.MultiIndex(levels=[[],[]], codes=[[],[]], names=["file","scenario"]))
    for file in pickle_files:
        data = pickle.load(open(rf"C:\Users\jonull\git\python\PickleJar\{file}.pickle", "rb"))
        #print(data['brit_lowFlex_noFC_2020_3h'].keys())
        for scen in data:
            df.loc[(file,scen),:] = data[scen]["cost_tot"]
    return df


"""
df = test2()
#print(tabulate.tabulate(df))
#print(tabulate.tabulate(df, headers="keys", tablefmt="grid"))
print(tabulate.tabulate(df, headers="keys", tablefmt="psql"))
#print(df.to_string())
"""


def export():
    data = pickle.load(open(r"C:\Users\jonull\git\python\PickleJar\data_results_6h_rerun.pickle", "rb"))
    for flex in ["lowFlex", "highFlex"]:
        print_green(f" -- {flex} --")
        for region in ["nordic","brit","iberia"]:
            for year in [2020,2025,2030,2040]:
                print_cyan(f"{region.capitalize()} - {year}")
                scenarios = [f"{region}_{flex}_{FC}_{year}_6h" for FC in ["noFC","fullFC"]]
                export = [data[scenario]["export_regional"] for scenario in scenarios]
                diff = 100*(export[1]-export[0])/export[0]
                FR_net_import = data[scenarios[1]]["FR_net_import"]
                FR_price = data[scenarios[1]]["FR_cost"]
                net_import_value = FR_net_import * FR_price
                all_import_value = FR_net_import[FR_net_import>0].fillna(value=0) * FR_price
                #print(FR_net_import.iloc[:,:7])
                #print(FR_price.iloc[:, :7])
                #print(net_import_value.iloc[:, :7])
                df = pd.DataFrame({"noFC":export[0], "fullFC":export[1], "diff":diff,
                                   "value_net":net_import_value.sum(axis='columns').sum(level='I_reg'),
                                  "value_all":all_import_value.sum(axis='columns').sum(level='I_reg')})
                df.loc["total"] = df.loc[:].sum()
                df.loc["total","diff"] = ((df.loc["total","fullFC"]-df.loc["total","noFC"])/df.loc["total","noFC"])*100
                #   print(f"FR import value: {export_revenue.sum(axis='columns').sum(level='I_reg')}")
                print(df.round(2))


export()