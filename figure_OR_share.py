import pickle
from os import path

import matplotlib.pyplot as plt
import pandas as pd


def percent_stacked_area(region, mode, timestep, indicator_string: str, set: dict, years=None, FC=True, secondary_y="FR_cost"):
    if years is None:
        years = [2020, 2025, 2030, 2040]
    data = pickle.load(open(path.relpath(rf"PickleJar\data_results_{timestep}h.pickle"), "rb"))
    scenarios = [f"{region}_{mode}_{'fullFC' if FC else 'noFC'}_{y}_{timestep}h" for y in years]
    if indicator_string == "FR_cost":
        indicator_data = {pretty: [0. for i in range(len(scenarios))] for pretty in set}
        for pretty, name in set.items():
            for i, scen in enumerate(scenarios):
                try: indicator_data[pretty][i] = data[scen]["FR_cost"].sum(axis=1).sum(level=1)[str(name)]
                except KeyError: indicator_data[pretty][i] = 0
                except ValueError:
                    print("!! weird formatting in FR_cost !!")
                    try: indicator_data[pretty][i] = data[scen]["FR_cost"].sum(level=2)[str(name)]
                    except Exception as e: print(type(e),e)
    else:
        indicator_data = {pretty: [data[scen][f"{indicator_string}{name}"] for scen in scenarios] for pretty, name in set.items()}
    secondary_y_values = [data[scen][secondary_y].sum().sum().round()/1000 for scen in scenarios]
    df = pd.DataFrame(data=
                      {pretty_name: indicator_data[pretty_name] for pretty_name in indicator_data}
                      , index=years).round(decimals=4)
    print(indicator_string)
    print(df)
    print(f"{secondary_y}: {secondary_y_values}")

    # ---- plotting
    # takes DataFrame and plots stacked area and optionally a line on secondary y axis
    ax = df.div(df.sum(axis=1), axis=0).plot(kind="area", linewidth=0)
    ax.set_xticks(df.index)
    if indicator_string == "FR_cost":
        ax.set_title(f"Interval share and cost, {region.capitalize()}, {mode}")
    else:
        ax.set_title(f"Reserve share and cost, {region.capitalize()}, {mode}")
    ax.set_ylabel("Share [-]")
    ax.set_xlabel("Year")
    current_handles, current_labels = plt.gca().get_legend_handles_labels()
    ax2 = ax.twinx()
    ax2.set_ylabel("Total reserve cost per year [M€]")
    line = ax2.plot(df.index, secondary_y_values, "k--", )
    handles = current_handles+line
    labels = [h.get_label() for h in handles]
    labels[-1] = "Cost"
    ax.legend(handles, labels)
    ax2.set_ylim(ymin=0)
    # ax2.ticklabel_format(style="sci", scilimits=(0, 0))
    return ax, ax2


mode = "lowFlex"
timestep = 6
reserve_technologies = {"Thermals": "thermal", "VRE": "VRE", "ESS": "ESS", "BEV": "BEV", "PtH": "PtH", "Hydro": "hydro"}
FR_intervals = {"FFR": 1, "5-30s": 2, "30s-5min": 3, "5-15min": 4, "15-30min": 5, "30-60min": 6}

for region in ["nordic", "brit", "iberia"]:
    print("_______________"*3)
    print(f" .. Making figure for {region} .. ")
    ax = percent_stacked_area(region, mode, timestep, "FR_value_share_", reserve_technologies)
    plt.savefig(rf"figures\reserve_valueshare_{region}_{mode}.png", dpi=600)
    ax = percent_stacked_area(region, mode, timestep, "FR_share_", reserve_technologies)
    plt.savefig(rf"figures\reserve_share_{region}_{mode}.png", dpi=600)
    ax = percent_stacked_area(region, mode, timestep, "FR_cost", FR_intervals)
    plt.savefig(rf"figures\interval_costs_{region}_{mode}.png", dpi=600)